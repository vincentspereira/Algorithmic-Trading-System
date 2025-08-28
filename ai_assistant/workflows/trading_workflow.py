"""
Trading Workflow for AI Assistant

This module defines LangGraph workflows for orchestrating trading operations
involving multiple specialized agents: Analyst, Risk Manager, and Trader.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, TypedDict
from datetime import datetime

from langgraph.graph import Graph, START, END
from langgraph.checkpoint.memory import MemorySaver

from ..agents.analyst_agent import AnalystAgent
from ..agents.risk_manager_agent import RiskManagerAgent
from ..agents.trader_agent import TraderAgent
from ..utils.workflow_utils import WorkflowState, WorkflowNode


logger = logging.getLogger(__name__)


class TradingWorkflowState(TypedDict):
    """State passed between nodes in the trading workflow"""
    request_id: str
    user_id: str
    symbol: str
    action: str  # "analyze", "execute_trade", "risk_check"
    market_data: Optional[Dict[str, Any]]
    analysis_result: Optional[Dict[str, Any]]
    risk_assessment: Optional[Dict[str, Any]]
    trade_decision: Optional[Dict[str, Any]]
    execution_result: Optional[Dict[str, Any]]
    errors: List[str]
    metadata: Dict[str, Any]


class TradingWorkflow:
    """
    LangGraph workflow for orchestrating trading operations
    
    This workflow coordinates between:
    - Analyst Agent: Market analysis and signal generation
    - Risk Manager Agent: Risk assessment and position sizing
    - Trader Agent: Trade execution and order management
    """
    
    def __init__(self):
        """Initialize the trading workflow"""
        self.analyst_agent = AnalystAgent()
        self.risk_manager_agent = RiskManagerAgent()
        self.trader_agent = TraderAgent()
        
        # Create workflow graph
        self.workflow = self._create_workflow()
        
        # Memory saver for checkpointing
        self.memory = MemorySaver()
        
        # Compile the workflow
        self.app = self.workflow.compile(checkpointer=self.memory)
        
        logger.info("Trading workflow initialized")
    
    def _create_workflow(self) -> Graph:
        """
        Create the LangGraph workflow
        
        Returns:
            Compiled workflow graph
        """
        # Create workflow graph
        workflow = Graph()
        
        # Add nodes
        workflow.add_node("market_analysis", self._market_analysis_node)
        workflow.add_node("risk_assessment", self._risk_assessment_node)
        workflow.add_node("trade_decision", self._trade_decision_node)
        workflow.add_node("trade_execution", self._trade_execution_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Define workflow edges
        workflow.add_edge(START, "market_analysis")
        workflow.add_edge("market_analysis", "risk_assessment")
        workflow.add_edge("risk_assessment", "trade_decision")
        workflow.add_edge("trade_decision", "trade_execution")
        workflow.add_edge("trade_execution", END)
        
        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "market_analysis",
            self._should_continue,
            {
                "continue": "risk_assessment",
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "risk_assessment",
            self._should_continue,
            {
                "continue": "trade_decision",
                "error": "error_handler"
            }
        )
        
        workflow.add_conditional_edges(
            "trade_decision",
            self._should_continue,
            {
                "continue": "trade_execution",
                "error": "error_handler"
            }
        )
        
        workflow.add_edge("error_handler", END)
        
        return workflow
    
    async def _market_analysis_node(self, state: TradingWorkflowState) -> TradingWorkflowState:
        """
        Market analysis node - delegates to Analyst Agent
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        try:
            logger.info(f"Starting market analysis for {state['symbol']}")
            
            # Prepare analysis request
            analysis_request = {
                "symbol": state["symbol"],
                "analysis_type": "comprehensive",
                "include_technical": True,
                "include_fundamental": True,
                "include_sentiment": True
            }
            
            # Execute analysis through Analyst Agent
            analysis_result = await self.analyst_agent.analyze_market(
                analysis_request,
                state.get("market_data")
            )
            
            # Update state
            state["analysis_result"] = analysis_result
            state["metadata"]["analysis_timestamp"] = datetime.utcnow().isoformat()
            
            logger.info(f"Market analysis completed for {state['symbol']}")
            
        except Exception as e:
            logger.error(f"Market analysis failed: {e}")
            state["errors"].append(f"Market analysis error: {str(e)}")
        
        return state
    
    async def _risk_assessment_node(self, state: TradingWorkflowState) -> TradingWorkflowState:
        """
        Risk assessment node - delegates to Risk Manager Agent
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        try:
            logger.info(f"Starting risk assessment for {state['symbol']}")
            
            # Prepare risk assessment request
            risk_request = {
                "symbol": state["symbol"],
                "analysis_result": state.get("analysis_result"),
                "portfolio_context": state.get("metadata", {}).get("portfolio_context"),
                "risk_tolerance": state.get("metadata", {}).get("risk_tolerance", "medium")
            }
            
            # Execute risk assessment through Risk Manager Agent
            risk_assessment = await self.risk_manager_agent.assess_risk(risk_request)
            
            # Update state
            state["risk_assessment"] = risk_assessment
            state["metadata"]["risk_assessment_timestamp"] = datetime.utcnow().isoformat()
            
            logger.info(f"Risk assessment completed for {state['symbol']}")
            
        except Exception as e:
            logger.error(f"Risk assessment failed: {e}")
            state["errors"].append(f"Risk assessment error: {str(e)}")
        
        return state
    
    async def _trade_decision_node(self, state: TradingWorkflowState) -> TradingWorkflowState:
        """
        Trade decision node - combines analysis and risk assessment
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        try:
            logger.info(f"Making trade decision for {state['symbol']}")
            
            analysis_result = state.get("analysis_result", {})
            risk_assessment = state.get("risk_assessment", {})
            
            # Make trade decision based on analysis and risk
            if analysis_result.get("recommendation") == "BUY" and risk_assessment.get("approved", False):
                trade_decision = {
                    "action": "BUY",
                    "quantity": risk_assessment.get("position_size", 0),
                    "order_type": "LIMIT",
                    "limit_price": analysis_result.get("target_price"),
                    "stop_loss": risk_assessment.get("stop_loss"),
                    "take_profit": risk_assessment.get("take_profit"),
                    "confidence": analysis_result.get("confidence", 0.5)
                }
            elif analysis_result.get("recommendation") == "SELL" and risk_assessment.get("approved", False):
                trade_decision = {
                    "action": "SELL",
                    "quantity": risk_assessment.get("position_size", 0),
                    "order_type": "LIMIT",
                    "limit_price": analysis_result.get("target_price"),
                    "confidence": analysis_result.get("confidence", 0.5)
                }
            else:
                trade_decision = {
                    "action": "HOLD",
                    "reason": "Analysis or risk assessment did not support trading action",
                    "confidence": 0.0
                }
            
            # Update state
            state["trade_decision"] = trade_decision
            state["metadata"]["trade_decision_timestamp"] = datetime.utcnow().isoformat()
            
            logger.info(f"Trade decision made for {state['symbol']}: {trade_decision['action']}")
            
        except Exception as e:
            logger.error(f"Trade decision failed: {e}")
            state["errors"].append(f"Trade decision error: {str(e)}")
        
        return state
    
    async def _trade_execution_node(self, state: TradingWorkflowState) -> TradingWorkflowState:
        """
        Trade execution node - delegates to Trader Agent
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        try:
            trade_decision = state.get("trade_decision", {})
            
            if trade_decision.get("action") in ["BUY", "SELL"]:
                logger.info(f"Executing trade for {state['symbol']}: {trade_decision['action']}")
                
                # Execute trade through Trader Agent
                execution_result = await self.trader_agent.execute_trade(
                    state["symbol"],
                    trade_decision
                )
                
                # Update state
                state["execution_result"] = execution_result
                state["metadata"]["execution_timestamp"] = datetime.utcnow().isoformat()
                
                logger.info(f"Trade executed for {state['symbol']}: {execution_result.get('status')}")
            else:
                logger.info(f"No trade execution needed for {state['symbol']}: {trade_decision.get('action', 'HOLD')}")
                state["execution_result"] = {
                    "status": "skipped",
                    "reason": "No trading action required"
                }
        
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            state["errors"].append(f"Trade execution error: {str(e)}")
        
        return state
    
    async def _error_handler_node(self, state: TradingWorkflowState) -> TradingWorkflowState:
        """
        Error handling node
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated workflow state
        """
        logger.error(f"Handling workflow errors for {state['symbol']}: {state['errors']}")
        
        # Log errors and prepare error response
        state["execution_result"] = {
            "status": "error",
            "errors": state["errors"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return state
    
    def _should_continue(self, state: TradingWorkflowState) -> str:
        """
        Determine if workflow should continue or handle errors
        
        Args:
            state: Current workflow state
            
        Returns:
            Next edge to follow
        """
        if state["errors"]:
            return "error"
        return "continue"
    
    async def execute_trading_workflow(
        self,
        request_id: str,
        user_id: str,
        symbol: str,
        action: str = "analyze_and_trade",
        market_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute the complete trading workflow
        
        Args:
            request_id: Unique request identifier
            user_id: User identifier
            symbol: Trading symbol
            action: Action to perform
            market_data: Optional market data
            metadata: Optional metadata
            
        Returns:
            Workflow execution result
        """
        # Initialize state
        initial_state: TradingWorkflowState = {
            "request_id": request_id,
            "user_id": user_id,
            "symbol": symbol,
            "action": action,
            "market_data": market_data,
            "analysis_result": None,
            "risk_assessment": None,
            "trade_decision": None,
            "execution_result": None,
            "errors": [],
            "metadata": metadata or {}
        }
        
        try:
            # Execute workflow
            logger.info(f"Starting trading workflow for {symbol} (request: {request_id})")
            
            result = await self.app.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": request_id}}
            )
            
            logger.info(f"Trading workflow completed for {symbol} (request: {request_id})")
            
            return {
                "request_id": request_id,
                "symbol": symbol,
                "status": "completed" if not result["errors"] else "error",
                "analysis_result": result.get("analysis_result"),
                "risk_assessment": result.get("risk_assessment"),
                "trade_decision": result.get("trade_decision"),
                "execution_result": result.get("execution_result"),
                "errors": result["errors"],
                "metadata": result["metadata"]
            }
        
        except Exception as e:
            logger.error(f"Trading workflow failed for {symbol}: {e}")
            return {
                "request_id": request_id,
                "symbol": symbol,
                "status": "error",
                "errors": [str(e)],
                "metadata": {"error_timestamp": datetime.utcnow().isoformat()}
            }