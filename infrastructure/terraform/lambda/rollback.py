import json
import boto3
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
ecs_client = boto3.client('ecs')
sns_client = boto3.client('sns')
cloudwatch_client = boto3.client('cloudwatch')

# Environment variables
CLUSTER_NAME = "${cluster_name}"
SERVICE_NAME = "${service_name}"
SNS_TOPIC_ARN = "${sns_topic_arn}"

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to handle automated rollback of failed ECS deployments.
    
    This function is triggered by EventBridge when an ECS deployment fails.
    It performs the following actions:
    1. Validates the deployment failure
    2. Retrieves the previous stable task definition
    3. Rolls back the service to the previous version
    4. Sends notifications about the rollback
    5. Records metrics for monitoring
    """
    try:
        logger.info(f"Rollback function triggered with event: {json.dumps(event)}")
        
        # Extract deployment information from the event
        deployment_info = extract_deployment_info(event)
        if not deployment_info:
            logger.error("Failed to extract deployment information from event")
            return create_response(400, "Invalid event format")
        
        # Validate that this is indeed a deployment failure
        if not is_deployment_failure(deployment_info):
            logger.info("Event is not a deployment failure, skipping rollback")
            return create_response(200, "Not a deployment failure")
        
        # Get current service configuration
        current_service = get_service_details(CLUSTER_NAME, SERVICE_NAME)
        if not current_service:
            logger.error(f"Failed to get service details for {SERVICE_NAME}")
            return create_response(500, "Failed to get service details")
        
        # Find the previous stable task definition
        previous_task_def = get_previous_stable_task_definition(
            current_service['taskDefinition']
        )
        if not previous_task_def:
            logger.error("No previous stable task definition found")
            return create_response(500, "No rollback target available")
        
        # Perform the rollback
        rollback_result = perform_rollback(
            CLUSTER_NAME, 
            SERVICE_NAME, 
            previous_task_def
        )
        
        if rollback_result['success']:
            # Send success notification
            send_notification(
                "Rollback Successful",
                f"Service {SERVICE_NAME} has been successfully rolled back to {previous_task_def}",
                "success"
            )
            
            # Record success metrics
            record_rollback_metrics("SUCCESS", deployment_info)
            
            logger.info(f"Rollback completed successfully to {previous_task_def}")
            return create_response(200, "Rollback completed successfully")
        else:
            # Send failure notification
            send_notification(
                "Rollback Failed",
                f"Failed to rollback service {SERVICE_NAME}: {rollback_result['error']}",
                "error"
            )
            
            # Record failure metrics
            record_rollback_metrics("FAILED", deployment_info)
            
            logger.error(f"Rollback failed: {rollback_result['error']}")
            return create_response(500, f"Rollback failed: {rollback_result['error']}")
            
    except Exception as e:
        logger.error(f"Unexpected error in rollback function: {str(e)}")
        
        # Send error notification
        send_notification(
            "Rollback Function Error",
            f"Rollback function encountered an error: {str(e)}",
            "error"
        )
        
        return create_response(500, f"Internal error: {str(e)}")

def extract_deployment_info(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract deployment information from the EventBridge event.
    """
    try:
        detail = event.get('detail', {})
        return {
            'cluster_arn': detail.get('clusterArn'),
            'service_arn': detail.get('serviceArn'),
            'deployment_id': detail.get('deploymentId'),
            'deployment_status': detail.get('deploymentStatus'),
            'task_definition': detail.get('taskDefinition'),
            'timestamp': event.get('time')
        }
    except Exception as e:
        logger.error(f"Error extracting deployment info: {str(e)}")
        return None

def is_deployment_failure(deployment_info: Dict[str, Any]) -> bool:
    """
    Check if the deployment status indicates a failure.
    """
    failure_statuses = ['FAILED', 'STOPPED']
    return deployment_info.get('deployment_status') in failure_statuses

def get_service_details(cluster_name: str, service_name: str) -> Optional[Dict[str, Any]]:
    """
    Get current service configuration from ECS.
    """
    try:
        response = ecs_client.describe_services(
            cluster=cluster_name,
            services=[service_name]
        )
        
        services = response.get('services', [])
        if not services:
            logger.error(f"Service {service_name} not found in cluster {cluster_name}")
            return None
            
        return services[0]
        
    except Exception as e:
        logger.error(f"Error getting service details: {str(e)}")
        return None

def get_previous_stable_task_definition(current_task_def_arn: str) -> Optional[str]:
    """
    Find the previous stable task definition for rollback.
    """
    try:
        # Extract family name from current task definition ARN
        family_name = current_task_def_arn.split('/')[-1].split(':')[0]
        
        # List all task definitions for this family
        response = ecs_client.list_task_definitions(
            familyPrefix=family_name,
            status='ACTIVE',
            sort='DESC'
        )
        
        task_definitions = response.get('taskDefinitionArns', [])
        
        # Find the previous version (skip the current one)
        for task_def_arn in task_definitions:
            if task_def_arn != current_task_def_arn:
                # Verify this task definition is stable
                if is_task_definition_stable(task_def_arn):
                    return task_def_arn
        
        logger.warning("No previous stable task definition found")
        return None
        
    except Exception as e:
        logger.error(f"Error finding previous task definition: {str(e)}")
        return None

def is_task_definition_stable(task_def_arn: str) -> bool:
    """
    Check if a task definition is considered stable for rollback.
    This is a simplified check - in production, you might want to
    check deployment history, health checks, etc.
    """
    try:
        # For now, we consider any previous task definition as stable
        # In a real implementation, you might check:
        # - Deployment success history
        # - Health check results
        # - Time since last successful deployment
        return True
        
    except Exception as e:
        logger.error(f"Error checking task definition stability: {str(e)}")
        return False

def perform_rollback(cluster_name: str, service_name: str, task_def_arn: str) -> Dict[str, Any]:
    """
    Perform the actual rollback by updating the ECS service.
    """
    try:
        logger.info(f"Starting rollback to task definition: {task_def_arn}")
        
        # Update the service with the previous task definition
        response = ecs_client.update_service(
            cluster=cluster_name,
            service=service_name,
            taskDefinition=task_def_arn,
            forceNewDeployment=True
        )
        
        deployment_id = None
        if 'service' in response and 'deployments' in response['service']:
            deployments = response['service']['deployments']
            if deployments:
                deployment_id = deployments[0].get('id')
        
        logger.info(f"Rollback initiated successfully. Deployment ID: {deployment_id}")
        
        return {
            'success': True,
            'deployment_id': deployment_id,
            'task_definition': task_def_arn
        }
        
    except Exception as e:
        logger.error(f"Error performing rollback: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def send_notification(subject: str, message: str, severity: str) -> None:
    """
    Send notification via SNS about the rollback status.
    """
    try:
        # Add timestamp and severity to the message
        timestamp = datetime.utcnow().isoformat()
        formatted_message = f"""
{message}

Timestamp: {timestamp}
Severity: {severity.upper()}
Cluster: {CLUSTER_NAME}
Service: {SERVICE_NAME}

This is an automated message from the deployment rollback system.
        """
        
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"[{severity.upper()}] {subject}",
            Message=formatted_message
        )
        
        logger.info(f"Notification sent: {subject}")
        
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")

def record_rollback_metrics(status: str, deployment_info: Dict[str, Any]) -> None:
    """
    Record rollback metrics in CloudWatch.
    """
    try:
        cloudwatch_client.put_metric_data(
            Namespace='AlgorithmicTrading/Deployment',
            MetricData=[
                {
                    'MetricName': 'RollbackAttempts',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {
                            'Name': 'ClusterName',
                            'Value': CLUSTER_NAME
                        },
                        {
                            'Name': 'ServiceName',
                            'Value': SERVICE_NAME
                        },
                        {
                            'Name': 'Status',
                            'Value': status
                        }
                    ]
                },
                {
                    'MetricName': 'RollbackLatency',
                    'Value': 1,  # This would be calculated based on actual timing
                    'Unit': 'Seconds',
                    'Dimensions': [
                        {
                            'Name': 'ClusterName',
                            'Value': CLUSTER_NAME
                        },
                        {
                            'Name': 'ServiceName',
                            'Value': SERVICE_NAME
                        }
                    ]
                }
            ]
        )
        
        logger.info(f"Rollback metrics recorded: {status}")
        
    except Exception as e:
        logger.error(f"Error recording metrics: {str(e)}")

def create_response(status_code: int, message: str) -> Dict[str, Any]:
    """
    Create a standardized Lambda response.
    """
    return {
        'statusCode': status_code,
        'body': json.dumps({
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'cluster': CLUSTER_NAME,
            'service': SERVICE_NAME
        })
    }