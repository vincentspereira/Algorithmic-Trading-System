#!/usr/bin/env python3
"""
Transaction Graph Analytics
Advanced graph-based analysis for detecting complex fraud patterns,
money laundering, and suspicious transaction networks.
"""

import asyncio
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import uuid
import networkx as nx
from networkx.algorithms import community
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PatternType(Enum):
    """Types of suspicious patterns"""
    CIRCULAR_TRANSACTION = "CIRCULAR_TRANSACTION"
    LAYERING = "LAYERING"
    SMURFING = "SMURFING"
    STRUCTURING = "STRUCTURING"
    RAPID_MOVEMENT = "RAPID_MOVEMENT"
    HUB_ACTIVITY = "HUB_ACTIVITY"
    BRIDGE_ACTIVITY = "BRIDGE_ACTIVITY"
    ISOLATED_CLUSTER = "ISOLATED_CLUSTER"
    VELOCITY_ANOMALY = "VELOCITY_ANOMALY"
    AMOUNT_ANOMALY = "AMOUNT_ANOMALY"

class RiskSeverity(Enum):
    """Risk severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

@dataclass
class TransactionNode:
    """Node representing a user/account in the transaction graph"""
    node_id: str
    user_id: str
    account_type: str
    created_at: datetime
    total_inflow: float = 0.0
    total_outflow: float = 0.0
    transaction_count: int = 0
    unique_counterparties: int = 0
    risk_score: float = 0.0
    is_suspicious: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TransactionEdge:
    """Edge representing a transaction between nodes"""
    edge_id: str
    from_node: str
    to_node: str
    amount: float
    timestamp: datetime
    transaction_type: str
    currency: str = "USD"
    reference: Optional[str] = None
    is_suspicious: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SuspiciousPattern:
    """Detected suspicious pattern"""
    pattern_id: str
    pattern_type: PatternType
    severity: RiskSeverity
    confidence: float
    description: str
    involved_nodes: List[str]
    involved_edges: List[str]
    detected_at: datetime
    total_amount: float
    time_span_hours: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

@dataclass
class CommunityAnalysis:
    """Community detection analysis results"""
    community_id: str
    members: List[str]
    internal_transactions: int
    external_transactions: int
    total_internal_amount: float
    total_external_amount: float
    density: float
    modularity: float
    is_suspicious: bool = False
    risk_factors: List[str] = field(default_factory=list)

class TransactionGraphAnalytics:
    """Advanced transaction graph analytics engine"""
    
    def __init__(self):
        self.graph = nx.DiGraph()  # Directed graph for transactions
        self.nodes: Dict[str, TransactionNode] = {}
        self.edges: Dict[str, TransactionEdge] = {}
        self.patterns: List[SuspiciousPattern] = []
        self.communities: List[CommunityAnalysis] = []
        
        # Configuration
        self.config = {
            'circular_transaction_threshold': 3,  # Minimum cycle length
            'layering_depth_threshold': 5,
            'smurfing_amount_threshold': 10000,
            'smurfing_count_threshold': 10,
            'rapid_movement_hours': 24,
            'hub_degree_threshold': 20,
            'velocity_threshold_per_hour': 100000,
            'amount_deviation_threshold': 3.0,
            'community_modularity_threshold': 0.3
        }
        
        logger.info("Transaction Graph Analytics initialized")
    
    def add_transaction(self, from_user: str, to_user: str, amount: float, 
                       timestamp: datetime, transaction_type: str = "TRANSFER",
                       currency: str = "USD", reference: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add transaction to the graph"""
        
        # Create edge
        edge_id = str(uuid.uuid4())
        edge = TransactionEdge(
            edge_id=edge_id,
            from_node=from_user,
            to_node=to_user,
            amount=amount,
            timestamp=timestamp,
            transaction_type=transaction_type,
            currency=currency,
            reference=reference,
            metadata=metadata or {}
        )
        
        self.edges[edge_id] = edge
        
        # Add nodes if they don't exist
        if from_user not in self.nodes:
            self.nodes[from_user] = TransactionNode(
                node_id=from_user,
                user_id=from_user,
                account_type="USER",
                created_at=timestamp
            )
        
        if to_user not in self.nodes:
            self.nodes[to_user] = TransactionNode(
                node_id=to_user,
                user_id=to_user,
                account_type="USER",
                created_at=timestamp
            )
        
        # Update node statistics
        from_node = self.nodes[from_user]
        to_node = self.nodes[to_user]
        
        from_node.total_outflow += amount
        from_node.transaction_count += 1
        
        to_node.total_inflow += amount
        to_node.transaction_count += 1
        
        # Add edge to NetworkX graph
        self.graph.add_edge(from_user, to_user, 
                           weight=amount, 
                           timestamp=timestamp,
                           edge_id=edge_id,
                           transaction_type=transaction_type)
        
        # Update unique counterparties
        self._update_counterparties()
        
        logger.debug(f"Added transaction: {from_user} -> {to_user}, Amount: {amount}")
        return edge_id
    
    def _update_counterparties(self):
        """Update unique counterparties count for all nodes"""
        for node_id in self.nodes:
            predecessors = set(self.graph.predecessors(node_id))
            successors = set(self.graph.successors(node_id))
            self.nodes[node_id].unique_counterparties = len(predecessors | successors)
    
    def detect_circular_transactions(self, min_cycle_length: int = 3) -> List[SuspiciousPattern]:
        """Detect circular transaction patterns (potential money laundering)"""
        patterns = []
        
        try:
            # Find all simple cycles
            cycles = list(nx.simple_cycles(self.graph))
            
            for cycle in cycles:
                if len(cycle) >= min_cycle_length:
                    # Calculate cycle statistics
                    total_amount = 0.0
                    timestamps = []
                    involved_edges = []
                    
                    for i in range(len(cycle)):
                        from_node = cycle[i]
                        to_node = cycle[(i + 1) % len(cycle)]
                        
                        if self.graph.has_edge(from_node, to_node):
                            edge_data = self.graph[from_node][to_node]
                            total_amount += edge_data.get('weight', 0)
                            timestamps.append(edge_data.get('timestamp'))
                            involved_edges.append(edge_data.get('edge_id'))
                    
                    if timestamps:
                        time_span = (max(timestamps) - min(timestamps)).total_seconds() / 3600
                        
                        # Determine severity based on amount and time span
                        if total_amount > 100000 and time_span < 24:
                            severity = RiskSeverity.CRITICAL
                        elif total_amount > 50000 and time_span < 48:
                            severity = RiskSeverity.HIGH
                        elif total_amount > 10000:
                            severity = RiskSeverity.MEDIUM
                        else:
                            severity = RiskSeverity.LOW
                        
                        pattern = SuspiciousPattern(
                            pattern_id=str(uuid.uuid4()),
                            pattern_type=PatternType.CIRCULAR_TRANSACTION,
                            severity=severity,
                            confidence=0.8 + (min(total_amount / 100000, 0.2)),
                            description=f"Circular transaction involving {len(cycle)} accounts with total amount ${total_amount:,.2f}",
                            involved_nodes=cycle,
                            involved_edges=involved_edges,
                            detected_at=datetime.now(),
                            total_amount=total_amount,
                            time_span_hours=time_span,
                            evidence={
                                'cycle_length': len(cycle),
                                'cycle_path': cycle,
                                'average_amount_per_hop': total_amount / len(cycle),
                                'completion_time_hours': time_span
                            },
                            recommendations=[
                                "Investigate the business relationship between involved parties",
                                "Review the purpose of circular transactions",
                                "Check for legitimate business reasons",
                                "Consider filing suspicious activity report if no valid reason found"
                            ]
                        )
                        
                        patterns.append(pattern)
        
        except Exception as e:
            logger.error(f"Error detecting circular transactions: {e}")
        
        return patterns
    
    def detect_layering_patterns(self, max_depth: int = 10) -> List[SuspiciousPattern]:
        """Detect layering patterns (complex transaction chains)"""
        patterns = []
        
        try:
            # Find long paths that might indicate layering
            for source in self.nodes:
                # Use DFS to find paths of significant length
                paths = self._find_long_paths(source, max_depth)
                
                for path in paths:
                    if len(path) >= self.config['layering_depth_threshold']:
                        # Analyze the path
                        total_amount = 0.0
                        timestamps = []
                        involved_edges = []
                        
                        for i in range(len(path) - 1):
                            from_node = path[i]
                            to_node = path[i + 1]
                            
                            if self.graph.has_edge(from_node, to_node):
                                edge_data = self.graph[from_node][to_node]
                                total_amount += edge_data.get('weight', 0)
                                timestamps.append(edge_data.get('timestamp'))
                                involved_edges.append(edge_data.get('edge_id'))
                        
                        if timestamps and total_amount > 10000:
                            time_span = (max(timestamps) - min(timestamps)).total_seconds() / 3600
                            
                            # Check for rapid layering (suspicious)
                            if time_span < 72 and len(path) >= 5:
                                severity = RiskSeverity.HIGH if time_span < 24 else RiskSeverity.MEDIUM
                                
                                pattern = SuspiciousPattern(
                                    pattern_id=str(uuid.uuid4()),
                                    pattern_type=PatternType.LAYERING,
                                    severity=severity,
                                    confidence=0.7 + (len(path) / 20),
                                    description=f"Layering pattern with {len(path)} hops and ${total_amount:,.2f} total amount",
                                    involved_nodes=path,
                                    involved_edges=involved_edges,
                                    detected_at=datetime.now(),
                                    total_amount=total_amount,
                                    time_span_hours=time_span,
                                    evidence={
                                        'path_length': len(path),
                                        'path': path,
                                        'average_amount_per_hop': total_amount / (len(path) - 1),
                                        'layering_speed_hours': time_span
                                    },
                                    recommendations=[
                                        "Investigate the purpose of complex transaction chain",
                                        "Verify legitimate business relationships",
                                        "Check for obfuscation of fund sources",
                                        "Review compliance with AML regulations"
                                    ]
                                )
                                
                                patterns.append(pattern)
        
        except Exception as e:
            logger.error(f"Error detecting layering patterns: {e}")
        
        return patterns
    
    def _find_long_paths(self, source: str, max_depth: int) -> List[List[str]]:
        """Find paths of significant length from a source node"""
        paths = []
        
        def dfs(current_path, visited, depth):
            if depth >= max_depth:
                return
            
            current_node = current_path[-1]
            
            for neighbor in self.graph.successors(current_node):
                if neighbor not in visited:
                    new_path = current_path + [neighbor]
                    new_visited = visited | {neighbor}
                    
                    if len(new_path) >= 3:  # Minimum interesting path length
                        paths.append(new_path.copy())
                    
                    dfs(new_path, new_visited, depth + 1)
        
        dfs([source], {source}, 0)
        return paths
    
    def detect_smurfing_patterns(self, time_window_hours: int = 24) -> List[SuspiciousPattern]:
        """Detect smurfing patterns (many small transactions to avoid reporting)"""
        patterns = []
        
        try:
            # Group transactions by time windows
            time_windows = defaultdict(list)
            
            for edge_id, edge in self.edges.items():
                window_key = edge.timestamp.replace(minute=0, second=0, microsecond=0)
                time_windows[window_key].append(edge)
            
            # Analyze each time window
            for window_time, transactions in time_windows.items():
                # Group by source account
                source_groups = defaultdict(list)
                for tx in transactions:
                    source_groups[tx.from_node].append(tx)
                
                for source, source_txs in source_groups.items():
                    if len(source_txs) >= self.config['smurfing_count_threshold']:
                        total_amount = sum(tx.amount for tx in source_txs)
                        avg_amount = total_amount / len(source_txs)
                        
                        # Check if amounts are consistently below reporting threshold
                        below_threshold = sum(1 for tx in source_txs 
                                            if tx.amount < self.config['smurfing_amount_threshold'])
                        
                        if (below_threshold / len(source_txs)) > 0.8:  # 80% below threshold
                            severity = RiskSeverity.HIGH if total_amount > 100000 else RiskSeverity.MEDIUM
                            
                            pattern = SuspiciousPattern(
                                pattern_id=str(uuid.uuid4()),
                                pattern_type=PatternType.SMURFING,
                                severity=severity,
                                confidence=0.75 + (below_threshold / len(source_txs)) * 0.25,
                                description=f"Smurfing pattern: {len(source_txs)} transactions totaling ${total_amount:,.2f}",
                                involved_nodes=[source] + list(set(tx.to_node for tx in source_txs)),
                                involved_edges=[tx.edge_id for tx in source_txs],
                                detected_at=datetime.now(),
                                total_amount=total_amount,
                                time_span_hours=time_window_hours,
                                evidence={
                                    'transaction_count': len(source_txs),
                                    'average_amount': avg_amount,
                                    'below_threshold_ratio': below_threshold / len(source_txs),
                                    'unique_recipients': len(set(tx.to_node for tx in source_txs)),
                                    'time_window': window_time.isoformat()
                                },
                                recommendations=[
                                    "Investigate if transactions are structured to avoid reporting",
                                    "Review customer due diligence documentation",
                                    "Check for legitimate business purpose",
                                    "Consider aggregating transactions for reporting purposes"
                                ]
                            )
                            
                            patterns.append(pattern)
        
        except Exception as e:
            logger.error(f"Error detecting smurfing patterns: {e}")
        
        return patterns
    
    def detect_hub_activity(self) -> List[SuspiciousPattern]:
        """Detect hub nodes with unusually high transaction activity"""
        patterns = []
        
        try:
            # Calculate degree centrality
            in_degree = dict(self.graph.in_degree())
            out_degree = dict(self.graph.out_degree())
            
            for node_id in self.nodes:
                total_degree = in_degree.get(node_id, 0) + out_degree.get(node_id, 0)
                
                if total_degree >= self.config['hub_degree_threshold']:
                    node = self.nodes[node_id]
                    
                    # Calculate additional metrics
                    betweenness = nx.betweenness_centrality(self.graph).get(node_id, 0)
                    
                    # Determine if this is suspicious
                    total_volume = node.total_inflow + node.total_outflow
                    avg_transaction = total_volume / max(node.transaction_count, 1)
                    
                    # High degree with low average transaction might indicate money mule
                    if avg_transaction < 5000 and total_degree > 50:
                        severity = RiskSeverity.HIGH
                    elif total_degree > 100:
                        severity = RiskSeverity.MEDIUM
                    else:
                        severity = RiskSeverity.LOW
                    
                    pattern = SuspiciousPattern(
                        pattern_id=str(uuid.uuid4()),
                        pattern_type=PatternType.HUB_ACTIVITY,
                        severity=severity,
                        confidence=0.6 + min(betweenness, 0.4),
                        description=f"Hub activity: {total_degree} connections with ${total_volume:,.2f} total volume",
                        involved_nodes=[node_id],
                        involved_edges=[],
                        detected_at=datetime.now(),
                        total_amount=total_volume,
                        time_span_hours=0,
                        evidence={
                            'total_degree': total_degree,
                            'in_degree': in_degree.get(node_id, 0),
                            'out_degree': out_degree.get(node_id, 0),
                            'betweenness_centrality': betweenness,
                            'average_transaction_amount': avg_transaction,
                            'unique_counterparties': node.unique_counterparties
                        },
                        recommendations=[
                            "Investigate the business model of high-activity account",
                            "Verify customer due diligence documentation",
                            "Check for money mule activity",
                            "Review transaction patterns for legitimacy"
                        ]
                    )
                    
                    patterns.append(pattern)
        
        except Exception as e:
            logger.error(f"Error detecting hub activity: {e}")
        
        return patterns
    
    def detect_velocity_anomalies(self, time_window_hours: int = 24) -> List[SuspiciousPattern]:
        """Detect unusual transaction velocity patterns"""
        patterns = []
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
            
            # Group recent transactions by user
            user_transactions = defaultdict(list)
            for edge in self.edges.values():
                if edge.timestamp >= cutoff_time:
                    user_transactions[edge.from_node].append(edge)
            
            # Analyze velocity for each user
            for user_id, transactions in user_transactions.items():
                if len(transactions) >= 5:  # Minimum transactions for analysis
                    total_amount = sum(tx.amount for tx in transactions)
                    velocity = total_amount / time_window_hours
                    
                    if velocity > self.config['velocity_threshold_per_hour']:
                        # Calculate additional metrics
                        avg_amount = total_amount / len(transactions)
                        unique_recipients = len(set(tx.to_node for tx in transactions))
                        
                        severity = RiskSeverity.CRITICAL if velocity > 500000 else RiskSeverity.HIGH
                        
                        pattern = SuspiciousPattern(
                            pattern_id=str(uuid.uuid4()),
                            pattern_type=PatternType.VELOCITY_ANOMALY,
                            severity=severity,
                            confidence=0.8 + min(velocity / 1000000, 0.2),
                            description=f"High velocity: ${velocity:,.2f}/hour over {time_window_hours} hours",
                            involved_nodes=[user_id] + list(set(tx.to_node for tx in transactions)),
                            involved_edges=[tx.edge_id for tx in transactions],
                            detected_at=datetime.now(),
                            total_amount=total_amount,
                            time_span_hours=time_window_hours,
                            evidence={
                                'velocity_per_hour': velocity,
                                'transaction_count': len(transactions),
                                'average_amount': avg_amount,
                                'unique_recipients': unique_recipients,
                                'time_window_hours': time_window_hours
                            },
                            recommendations=[
                                "Investigate the source of high-velocity transactions",
                                "Verify business justification for rapid fund movement",
                                "Check for automated trading or business operations",
                                "Consider temporary transaction limits pending review"
                            ]
                        )
                        
                        patterns.append(pattern)
        
        except Exception as e:
            logger.error(f"Error detecting velocity anomalies: {e}")
        
        return patterns
    
    def perform_community_detection(self) -> List[CommunityAnalysis]:
        """Perform community detection to identify transaction clusters"""
        communities = []
        
        try:
            # Convert to undirected graph for community detection
            undirected_graph = self.graph.to_undirected()
            
            # Use Louvain method for community detection
            community_partition = community.greedy_modularity_communities(undirected_graph)
            
            for i, comm in enumerate(community_partition):
                members = list(comm)
                
                if len(members) >= 3:  # Minimum community size
                    # Calculate community statistics
                    internal_transactions = 0
                    external_transactions = 0
                    total_internal_amount = 0.0
                    total_external_amount = 0.0
                    
                    for member in members:
                        for neighbor in self.graph.successors(member):
                            edge_data = self.graph[member][neighbor]
                            amount = edge_data.get('weight', 0)
                            
                            if neighbor in members:
                                internal_transactions += 1
                                total_internal_amount += amount
                            else:
                                external_transactions += 1
                                total_external_amount += amount
                    
                    # Calculate density
                    possible_edges = len(members) * (len(members) - 1)
                    actual_edges = internal_transactions
                    density = actual_edges / max(possible_edges, 1)
                    
                    # Calculate modularity for this community
                    subgraph = undirected_graph.subgraph(members)
                    modularity = nx.algorithms.community.modularity(undirected_graph, [comm])
                    
                    # Determine if community is suspicious
                    is_suspicious = False
                    risk_factors = []
                    
                    # High internal activity with low external activity
                    if (internal_transactions > external_transactions * 3 and 
                        total_internal_amount > 50000):
                        is_suspicious = True
                        risk_factors.append("High internal transaction ratio")
                    
                    # High density communities might indicate coordinated activity
                    if density > 0.7 and len(members) > 5:
                        is_suspicious = True
                        risk_factors.append("High community density")
                    
                    # High modularity might indicate isolated group
                    if modularity > self.config['community_modularity_threshold']:
                        risk_factors.append("High modularity (isolated group)")
                    
                    community_analysis = CommunityAnalysis(
                        community_id=f"community_{i}",
                        members=members,
                        internal_transactions=internal_transactions,
                        external_transactions=external_transactions,
                        total_internal_amount=total_internal_amount,
                        total_external_amount=total_external_amount,
                        density=density,
                        modularity=modularity,
                        is_suspicious=is_suspicious,
                        risk_factors=risk_factors
                    )
                    
                    communities.append(community_analysis)
        
        except Exception as e:
            logger.error(f"Error in community detection: {e}")
        
        self.communities = communities
        return communities
    
    def analyze_all_patterns(self) -> Dict[str, List[SuspiciousPattern]]:
        """Run all pattern detection algorithms"""
        all_patterns = {
            'circular_transactions': self.detect_circular_transactions(),
            'layering_patterns': self.detect_layering_patterns(),
            'smurfing_patterns': self.detect_smurfing_patterns(),
            'hub_activity': self.detect_hub_activity(),
            'velocity_anomalies': self.detect_velocity_anomalies()
        }
        
        # Flatten all patterns
        self.patterns = []
        for pattern_type, patterns in all_patterns.items():
            self.patterns.extend(patterns)
        
        logger.info(f"Detected {len(self.patterns)} suspicious patterns across all categories")
        return all_patterns
    
    def get_node_risk_score(self, node_id: str) -> float:
        """Calculate comprehensive risk score for a node"""
        if node_id not in self.nodes:
            return 0.0
        
        node = self.nodes[node_id]
        risk_score = 0.0
        
        # Volume-based risk
        total_volume = node.total_inflow + node.total_outflow
        if total_volume > 1000000:
            risk_score += 0.2
        elif total_volume > 100000:
            risk_score += 0.1
        
        # Activity-based risk
        if node.transaction_count > 100:
            risk_score += 0.15
        elif node.transaction_count > 50:
            risk_score += 0.1
        
        # Counterparty diversity risk
        if node.unique_counterparties > 50:
            risk_score += 0.15
        elif node.unique_counterparties > 20:
            risk_score += 0.1
        
        # Pattern involvement risk
        pattern_involvement = sum(1 for pattern in self.patterns 
                                if node_id in pattern.involved_nodes)
        risk_score += min(pattern_involvement * 0.1, 0.3)
        
        # Network centrality risk
        try:
            betweenness = nx.betweenness_centrality(self.graph).get(node_id, 0)
            risk_score += betweenness * 0.2
        except:
            pass
        
        node.risk_score = min(risk_score, 1.0)
        return node.risk_score
    
    def generate_risk_report(self, node_id: str) -> Dict[str, Any]:
        """Generate comprehensive risk report for a node"""
        if node_id not in self.nodes:
            return {'error': 'Node not found'}
        
        node = self.nodes[node_id]
        risk_score = self.get_node_risk_score(node_id)
        
        # Find patterns involving this node
        involved_patterns = [p for p in self.patterns if node_id in p.involved_nodes]
        
        # Calculate network metrics
        try:
            in_degree = self.graph.in_degree(node_id)
            out_degree = self.graph.out_degree(node_id)
            betweenness = nx.betweenness_centrality(self.graph).get(node_id, 0)
            closeness = nx.closeness_centrality(self.graph).get(node_id, 0)
        except:
            in_degree = out_degree = betweenness = closeness = 0
        
        # Find community membership
        community_membership = None
        for comm in self.communities:
            if node_id in comm.members:
                community_membership = comm
                break
        
        report = {
            'node_id': node_id,
            'risk_score': risk_score,
            'risk_level': 'HIGH' if risk_score > 0.7 else 'MEDIUM' if risk_score > 0.4 else 'LOW',
            'node_statistics': {
                'total_inflow': node.total_inflow,
                'total_outflow': node.total_outflow,
                'net_flow': node.total_inflow - node.total_outflow,
                'transaction_count': node.transaction_count,
                'unique_counterparties': node.unique_counterparties,
                'account_age_days': (datetime.now() - node.created_at).days
            },
            'network_metrics': {
                'in_degree': in_degree,
                'out_degree': out_degree,
                'total_degree': in_degree + out_degree,
                'betweenness_centrality': betweenness,
                'closeness_centrality': closeness
            },
            'pattern_involvement': {
                'total_patterns': len(involved_patterns),
                'pattern_types': list(set(p.pattern_type.value for p in involved_patterns)),
                'highest_severity': max([p.severity.value for p in involved_patterns], default='LOW')
            },
            'community_analysis': {
                'community_id': community_membership.community_id if community_membership else None,
                'community_size': len(community_membership.members) if community_membership else 0,
                'community_suspicious': community_membership.is_suspicious if community_membership else False
            },
            'recommendations': self._generate_node_recommendations(node, risk_score, involved_patterns)
        }
        
        return report
    
    def _generate_node_recommendations(self, node: TransactionNode, risk_score: float, 
                                     patterns: List[SuspiciousPattern]) -> List[str]:
        """Generate recommendations based on node analysis"""
        recommendations = []
        
        if risk_score > 0.8:
            recommendations.append("Immediate investigation required - high risk score")
        elif risk_score > 0.6:
            recommendations.append("Enhanced monitoring and review recommended")
        
        if node.unique_counterparties > 100:
            recommendations.append("Review business model - unusually high counterparty count")
        
        if node.total_inflow + node.total_outflow > 1000000:
            recommendations.append("High-value account - ensure enhanced due diligence")
        
        pattern_types = set(p.pattern_type for p in patterns)
        if PatternType.CIRCULAR_TRANSACTION in pattern_types:
            recommendations.append("Investigate circular transaction patterns for money laundering")
        if PatternType.LAYERING in pattern_types:
            recommendations.append("Review complex transaction chains for obfuscation")
        if PatternType.SMURFING in pattern_types:
            recommendations.append("Check for structuring to avoid reporting requirements")
        
        if not recommendations:
            recommendations.append("Continue regular monitoring")
        
        return recommendations
    
    def export_graph_data(self, format: str = "json") -> str:
        """Export graph data in specified format"""
        if format.lower() == "json":
            data = {
                'nodes': [
                    {
                        'id': node.node_id,
                        'user_id': node.user_id,
                        'total_inflow': node.total_inflow,
                        'total_outflow': node.total_outflow,
                        'transaction_count': node.transaction_count,
                        'risk_score': node.risk_score,
                        'is_suspicious': node.is_suspicious
                    }
                    for node in self.nodes.values()
                ],
                'edges': [
                    {
                        'id': edge.edge_id,
                        'from': edge.from_node,
                        'to': edge.to_node,
                        'amount': edge.amount,
                        'timestamp': edge.timestamp.isoformat(),
                        'transaction_type': edge.transaction_type,
                        'is_suspicious': edge.is_suspicious
                    }
                    for edge in self.edges.values()
                ],
                'patterns': [
                    {
                        'id': pattern.pattern_id,
                        'type': pattern.pattern_type.value,
                        'severity': pattern.severity.value,
                        'confidence': pattern.confidence,
                        'description': pattern.description,
                        'total_amount': pattern.total_amount,
                        'involved_nodes': pattern.involved_nodes
                    }
                    for pattern in self.patterns
                ]
            }
            return json.dumps(data, indent=2)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary"""
        return {
            'graph_statistics': {
                'total_nodes': len(self.nodes),
                'total_edges': len(self.edges),
                'total_volume': sum(edge.amount for edge in self.edges.values()),
                'average_transaction_amount': np.mean([edge.amount for edge in self.edges.values()]) if self.edges else 0,
                'graph_density': nx.density(self.graph) if self.graph.number_of_nodes() > 0 else 0
            },
            'pattern_detection': {
                'total_patterns': len(self.patterns),
                'pattern_distribution': {
                    pattern_type.value: len([p for p in self.patterns if p.pattern_type == pattern_type])
                    for pattern_type in PatternType
                },
                'severity_distribution': {
                    severity.value: len([p for p in self.patterns if p.severity == severity])
                    for severity in RiskSeverity
                }
            },
            'community_analysis': {
                'total_communities': len(self.communities),
                'suspicious_communities': len([c for c in self.communities if c.is_suspicious]),
                'average_community_size': np.mean([len(c.members) for c in self.communities]) if self.communities else 0
            },
            'risk_distribution': {
                'high_risk_nodes': len([n for n in self.nodes.values() if n.risk_score > 0.7]),
                'medium_risk_nodes': len([n for n in self.nodes.values() if 0.4 < n.risk_score <= 0.7]),
                'low_risk_nodes': len([n for n in self.nodes.values() if n.risk_score <= 0.4])
            }
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize graph analytics
    graph_analytics = TransactionGraphAnalytics()
    
    # Add sample transactions
    users = ['user_1', 'user_2', 'user_3', 'user_4', 'user_5']
    
    # Create some normal transactions
    for i in range(20):
        from_user = np.random.choice(users)
        to_user = np.random.choice([u for u in users if u != from_user])
        amount = np.random.uniform(1000, 10000)
        timestamp = datetime.now() - timedelta(hours=np.random.uniform(0, 168))
        
        graph_analytics.add_transaction(from_user, to_user, amount, timestamp)
    
    # Create a suspicious circular transaction
    circular_amount = 50000
    timestamp = datetime.now() - timedelta(hours=2)
    graph_analytics.add_transaction('user_1', 'user_2', circular_amount, timestamp)
    graph_analytics.add_transaction('user_2', 'user_3', circular_amount * 0.95, timestamp + timedelta(minutes=30))
    graph_analytics.add_transaction('user_3', 'user_1', circular_amount * 0.9, timestamp + timedelta(hours=1))
    
    # Analyze patterns
    patterns = graph_analytics.analyze_all_patterns()
    
    print("Transaction Graph Analytics Results:")
    print("=" * 50)
    
    for pattern_type, pattern_list in patterns.items():
        print(f"\n{pattern_type.upper()}: {len(pattern_list)} patterns detected")
        for pattern in pattern_list:
            print(f"  - {pattern.description} (Severity: {pattern.severity.value})")
    
    # Get analytics summary
    summary = graph_analytics.get_analytics_summary()
    print(f"\nGraph Statistics:")
    print(f"  Nodes: {summary['graph_statistics']['total_nodes']}")
    print(f"  Edges: {summary['graph_statistics']['total_edges']}")
    print(f"  Total Volume: ${summary['graph_statistics']['total_volume']:,.2f}")
    print(f"  Total Patterns: {summary['pattern_detection']['total_patterns']}")
    
    # Generate risk report for a user
    risk_report = graph_analytics.generate_risk_report('user_1')
    print(f"\nRisk Report for user_1:")
    print(f"  Risk Score: {risk_report['risk_score']:.3f}")
    print(f"  Risk Level: {risk_report['risk_level']}")
    print(f"  Pattern Involvement: {risk_report['pattern_involvement']['total_patterns']} patterns")