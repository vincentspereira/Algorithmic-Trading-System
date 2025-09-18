#!/usr/bin/env python3
"""
Reinforcement Learning Strategies Module for Algorithmic Trading System

This module implements reinforcement learning-based trading strategies including
Q-Learning, Deep Q-Networks (DQN), Policy Gradient methods, and Actor-Critic algorithms.
It follows the 5-Pillar Architecture:
1. Data Management: Environment state representation and reward engineering
2. Strategy Logic: RL agents and policy networks
3. Risk Management: Risk-aware reward functions
4. Execution Management: Action space and position management
5. Performance Analytics: RL-specific performance metrics

Author: Algorithmic Trading System
Version: 1.0.0
Date: 2024
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Core ML libraries
try:
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. Using fallback preprocessing.")

# Deep learning libraries
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    from torch.distributions import Categorical
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not available. RL strategies will use simplified implementations.")

# Import feature engineering
from .feature_engineering import FeatureEngineer, FeatureConfig

class ActionType(Enum):
    """Trading action types"""
    HOLD = 0
    BUY = 1
    SELL = 2
    BUY_STRONG = 3
    SELL_STRONG = 4

class RLAlgorithm(Enum):
    """Reinforcement learning algorithm types"""
    Q_LEARNING = "q_learning"
    DQN = "dqn"
    DOUBLE_DQN = "double_dqn"
    DUELING_DQN = "dueling_dqn"
    POLICY_GRADIENT = "policy_gradient"
    ACTOR_CRITIC = "actor_critic"
    PPO = "ppo"
    A3C = "a3c"

@dataclass
class RLConfig:
    """Configuration for reinforcement learning strategies"""
    # Algorithm selection
    algorithm: RLAlgorithm = RLAlgorithm.DQN
    
    # Environment parameters
    lookback_window: int = 20
    action_space_size: int = 5  # Number of possible actions
    state_space_size: int = 50  # Number of features in state
    
    # Training parameters
    learning_rate: float = 0.001
    gamma: float = 0.95  # Discount factor
    epsilon: float = 1.0  # Exploration rate
    epsilon_min: float = 0.01
    epsilon_decay: float = 0.995
    
    # Network architecture
    hidden_layers: List[int] = field(default_factory=lambda: [128, 64, 32])
    dropout_rate: float = 0.2
    
    # Training settings
    batch_size: int = 32
    memory_size: int = 10000
    target_update_frequency: int = 100
    training_frequency: int = 4
    
    # Reward engineering
    reward_scaling: float = 1.0
    risk_penalty: float = 0.1
    transaction_cost: float = 0.001
    
    # Performance tracking
    evaluation_episodes: int = 100
    save_frequency: int = 1000

@dataclass
class TradingState:
    """Trading environment state"""
    features: np.ndarray
    position: float  # Current position (-1 to 1)
    cash: float
    portfolio_value: float
    unrealized_pnl: float
    drawdown: float
    timestamp: datetime
    market_data: Dict[str, float] = field(default_factory=dict)

@dataclass
class TradingAction:
    """Trading action with metadata"""
    action_type: ActionType
    position_size: float
    confidence: float
    expected_return: float
    risk_score: float
    timestamp: datetime

class ReplayBuffer:
    """Experience replay buffer for DQN"""
    
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buffer = []
        self.position = 0
    
    def push(self, state: np.ndarray, action: int, reward: float, 
             next_state: np.ndarray, done: bool):
        """Save a transition"""
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        
        self.buffer[self.position] = (state, action, reward, next_state, done)
        self.position = (self.position + 1) % self.capacity
    
    def sample(self, batch_size: int) -> Tuple[np.ndarray, ...]:
        """Sample a batch of transitions"""
        batch = np.random.choice(len(self.buffer), batch_size, replace=False)
        states, actions, rewards, next_states, dones = zip(*[self.buffer[i] for i in batch])
        
        return (
            np.array(states),
            np.array(actions),
            np.array(rewards),
            np.array(next_states),
            np.array(dones)
        )
    
    def __len__(self):
        return len(self.buffer)

class DQNNetwork(nn.Module):
    """Deep Q-Network for trading"""
    
    def __init__(self, state_size: int, action_size: int, hidden_layers: List[int], dropout_rate: float = 0.2):
        super(DQNNetwork, self).__init__()
        
        layers = []
        input_size = state_size
        
        # Hidden layers
        for hidden_size in hidden_layers:
            layers.extend([
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(dropout_rate)
            ])
            input_size = hidden_size
        
        # Output layer
        layers.append(nn.Linear(input_size, action_size))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)

class DuelingDQNNetwork(nn.Module):
    """Dueling DQN architecture"""
    
    def __init__(self, state_size: int, action_size: int, hidden_layers: List[int], dropout_rate: float = 0.2):
        super(DuelingDQNNetwork, self).__init__()
        
        # Shared feature layers
        feature_layers = []
        input_size = state_size
        
        for hidden_size in hidden_layers[:-1]:
            feature_layers.extend([
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(dropout_rate)
            ])
            input_size = hidden_size
        
        self.feature_layers = nn.Sequential(*feature_layers)
        
        # Value stream
        self.value_stream = nn.Sequential(
            nn.Linear(input_size, hidden_layers[-1]),
            nn.ReLU(),
            nn.Linear(hidden_layers[-1], 1)
        )
        
        # Advantage stream
        self.advantage_stream = nn.Sequential(
            nn.Linear(input_size, hidden_layers[-1]),
            nn.ReLU(),
            nn.Linear(hidden_layers[-1], action_size)
        )
    
    def forward(self, x):
        features = self.feature_layers(x)
        
        value = self.value_stream(features)
        advantage = self.advantage_stream(features)
        
        # Combine value and advantage
        q_values = value + (advantage - advantage.mean(dim=1, keepdim=True))
        
        return q_values

class PolicyNetwork(nn.Module):
    """Policy network for policy gradient methods"""
    
    def __init__(self, state_size: int, action_size: int, hidden_layers: List[int], dropout_rate: float = 0.2):
        super(PolicyNetwork, self).__init__()
        
        layers = []
        input_size = state_size
        
        # Hidden layers
        for hidden_size in hidden_layers:
            layers.extend([
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(dropout_rate)
            ])
            input_size = hidden_size
        
        # Output layer with softmax
        layers.extend([
            nn.Linear(input_size, action_size),
            nn.Softmax(dim=-1)
        ])
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)

class TradingEnvironment:
    """Trading environment for RL agents"""
    
    def __init__(self, data: pd.DataFrame, config: RLConfig):
        self.data = data
        self.config = config
        self.feature_engineer = FeatureEngineer(FeatureConfig())
        self.scaler = StandardScaler() if SKLEARN_AVAILABLE else None
        
        # Environment state
        self.current_step = 0
        self.initial_balance = 10000.0
        self.balance = self.initial_balance
        self.position = 0.0
        self.portfolio_value = self.initial_balance
        self.max_portfolio_value = self.initial_balance
        
        # Prepare features
        self._prepare_features()
        
        # Episode tracking
        self.episode_returns = []
        self.episode_actions = []
    
    def _prepare_features(self):
        """Prepare features for the environment"""
        try:
            # Extract technical features
            features = self.feature_engineer.create_technical_features(self.data)
            
            # Add price-based features
            features['returns'] = self.data['close'].pct_change()
            features['log_returns'] = np.log(self.data['close'] / self.data['close'].shift(1))
            features['volatility'] = features['returns'].rolling(20).std()
            
            # Add volume features if available
            if 'volume' in self.data.columns:
                features['volume_ratio'] = self.data['volume'] / self.data['volume'].rolling(20).mean()
            
            # Clean and normalize features
            features = features.fillna(method='ffill').fillna(0)
            features = features.replace([np.inf, -np.inf], 0)
            
            # Scale features
            if self.scaler is not None:
                feature_columns = features.select_dtypes(include=[np.number]).columns
                features[feature_columns] = self.scaler.fit_transform(features[feature_columns])
            
            self.features = features
            
        except Exception as e:
            logging.error(f"Error preparing features: {e}")
            # Fallback to basic features
            self.features = pd.DataFrame({
                'returns': self.data['close'].pct_change().fillna(0),
                'price': self.data['close'] / self.data['close'].iloc[0]
            })
    
    def reset(self) -> TradingState:
        """Reset environment to initial state"""
        self.current_step = self.config.lookback_window
        self.balance = self.initial_balance
        self.position = 0.0
        self.portfolio_value = self.initial_balance
        self.max_portfolio_value = self.initial_balance
        self.episode_returns = []
        self.episode_actions = []
        
        return self._get_state()
    
    def step(self, action: int) -> Tuple[TradingState, float, bool, Dict[str, Any]]:
        """Execute action and return new state, reward, done, info"""
        # Execute action
        reward = self._execute_action(action)
        
        # Update step
        self.current_step += 1
        
        # Check if episode is done
        done = self.current_step >= len(self.data) - 1
        
        # Get new state
        new_state = self._get_state()
        
        # Additional info
        info = {
            'portfolio_value': self.portfolio_value,
            'position': self.position,
            'balance': self.balance,
            'drawdown': (self.max_portfolio_value - self.portfolio_value) / self.max_portfolio_value
        }
        
        return new_state, reward, done, info
    
    def _execute_action(self, action: int) -> float:
        """Execute trading action and calculate reward"""
        current_price = self.data['close'].iloc[self.current_step]
        previous_price = self.data['close'].iloc[self.current_step - 1]
        
        # Map action to position change
        action_mapping = {
            ActionType.HOLD.value: 0.0,
            ActionType.BUY.value: 0.25,
            ActionType.SELL.value: -0.25,
            ActionType.BUY_STRONG.value: 0.5,
            ActionType.SELL_STRONG.value: -0.5
        }
        
        position_change = action_mapping.get(action, 0.0)
        new_position = np.clip(self.position + position_change, -1.0, 1.0)
        
        # Calculate transaction cost
        transaction_cost = abs(new_position - self.position) * self.config.transaction_cost
        
        # Update position and balance
        position_value = new_position * self.balance
        self.position = new_position
        
        # Calculate portfolio value
        price_change = (current_price - previous_price) / previous_price
        position_pnl = self.position * price_change * self.balance
        
        self.portfolio_value = self.balance + position_pnl - transaction_cost
        self.max_portfolio_value = max(self.max_portfolio_value, self.portfolio_value)
        
        # Calculate reward
        reward = self._calculate_reward(action, price_change, transaction_cost)
        
        # Record action
        self.episode_actions.append(action)
        self.episode_returns.append(price_change)
        
        return reward
    
    def _calculate_reward(self, action: int, price_change: float, transaction_cost: float) -> float:
        """Calculate reward for the action"""
        # Base reward from position and price change
        position_reward = self.position * price_change
        
        # Risk penalty for large positions
        risk_penalty = self.config.risk_penalty * abs(self.position) ** 2
        
        # Transaction cost penalty
        cost_penalty = transaction_cost
        
        # Drawdown penalty
        drawdown = (self.max_portfolio_value - self.portfolio_value) / self.max_portfolio_value
        drawdown_penalty = drawdown ** 2
        
        # Combine rewards
        total_reward = (
            position_reward * self.config.reward_scaling
            - risk_penalty
            - cost_penalty
            - drawdown_penalty
        )
        
        return total_reward
    
    def _get_state(self) -> TradingState:
        """Get current environment state"""
        # Get feature window
        start_idx = max(0, self.current_step - self.config.lookback_window)
        end_idx = self.current_step + 1
        
        feature_window = self.features.iloc[start_idx:end_idx]
        
        # Pad if necessary
        if len(feature_window) < self.config.lookback_window:
            padding = pd.DataFrame(
                np.zeros((self.config.lookback_window - len(feature_window), len(feature_window.columns))),
                columns=feature_window.columns
            )
            feature_window = pd.concat([padding, feature_window], ignore_index=True)
        
        # Flatten features
        features_flat = feature_window.values.flatten()
        
        # Add portfolio state
        portfolio_features = np.array([
            self.position,
            self.balance / self.initial_balance,
            self.portfolio_value / self.initial_balance,
            (self.max_portfolio_value - self.portfolio_value) / self.max_portfolio_value
        ])
        
        # Combine features
        state_features = np.concatenate([features_flat, portfolio_features])
        
        # Ensure fixed size
        if len(state_features) > self.config.state_space_size:
            state_features = state_features[:self.config.state_space_size]
        elif len(state_features) < self.config.state_space_size:
            padding = np.zeros(self.config.state_space_size - len(state_features))
            state_features = np.concatenate([state_features, padding])
        
        return TradingState(
            features=state_features,
            position=self.position,
            cash=self.balance,
            portfolio_value=self.portfolio_value,
            unrealized_pnl=self.portfolio_value - self.initial_balance,
            drawdown=(self.max_portfolio_value - self.portfolio_value) / self.max_portfolio_value,
            timestamp=datetime.now()
        )

class DQNAgent:
    """Deep Q-Network agent for trading"""
    
    def __init__(self, config: RLConfig):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        if not TORCH_AVAILABLE:
            logging.warning("PyTorch not available. DQN agent will use simplified implementation.")
            return
        
        # Initialize networks
        if config.algorithm == RLAlgorithm.DUELING_DQN:
            self.q_network = DuelingDQNNetwork(
                config.state_space_size,
                config.action_space_size,
                config.hidden_layers,
                config.dropout_rate
            ).to(self.device)
            
            self.target_network = DuelingDQNNetwork(
                config.state_space_size,
                config.action_space_size,
                config.hidden_layers,
                config.dropout_rate
            ).to(self.device)
        else:
            self.q_network = DQNNetwork(
                config.state_space_size,
                config.action_space_size,
                config.hidden_layers,
                config.dropout_rate
            ).to(self.device)
            
            self.target_network = DQNNetwork(
                config.state_space_size,
                config.action_space_size,
                config.hidden_layers,
                config.dropout_rate
            ).to(self.device)
        
        # Initialize optimizer
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=config.learning_rate)
        
        # Initialize replay buffer
        self.memory = ReplayBuffer(config.memory_size)
        
        # Training state
        self.epsilon = config.epsilon
        self.steps_done = 0
        self.training_step = 0
        
        # Update target network
        self.update_target_network()
    
    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """Select action using epsilon-greedy policy"""
        if not TORCH_AVAILABLE:
            return np.random.randint(0, self.config.action_space_size)
        
        if training and np.random.random() < self.epsilon:
            return np.random.randint(0, self.config.action_space_size)
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.q_network(state_tensor)
            return q_values.argmax().item()
    
    def store_transition(self, state: np.ndarray, action: int, reward: float, 
                       next_state: np.ndarray, done: bool):
        """Store transition in replay buffer"""
        self.memory.push(state, action, reward, next_state, done)
    
    def train(self) -> Optional[float]:
        """Train the DQN"""
        if not TORCH_AVAILABLE or len(self.memory) < self.config.batch_size:
            return None
        
        # Sample batch
        states, actions, rewards, next_states, dones = self.memory.sample(self.config.batch_size)
        
        # Convert to tensors
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(next_states).to(self.device)
        dones = torch.BoolTensor(dones).to(self.device)
        
        # Current Q values
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        
        # Next Q values
        with torch.no_grad():
            if self.config.algorithm == RLAlgorithm.DOUBLE_DQN:
                # Double DQN: use main network to select action, target network to evaluate
                next_actions = self.q_network(next_states).argmax(1)
                next_q_values = self.target_network(next_states).gather(1, next_actions.unsqueeze(1))
            else:
                # Standard DQN
                next_q_values = self.target_network(next_states).max(1)[0].unsqueeze(1)
            
            target_q_values = rewards.unsqueeze(1) + (self.config.gamma * next_q_values * ~dones.unsqueeze(1))
        
        # Compute loss
        loss = F.mse_loss(current_q_values, target_q_values)
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()
        
        # Update epsilon
        if self.epsilon > self.config.epsilon_min:
            self.epsilon *= self.config.epsilon_decay
        
        # Update target network
        self.training_step += 1
        if self.training_step % self.config.target_update_frequency == 0:
            self.update_target_network()
        
        return loss.item()
    
    def update_target_network(self):
        """Update target network with main network weights"""
        if TORCH_AVAILABLE:
            self.target_network.load_state_dict(self.q_network.state_dict())

class PolicyGradientAgent:
    """Policy Gradient agent for trading"""
    
    def __init__(self, config: RLConfig):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        if not TORCH_AVAILABLE:
            logging.warning("PyTorch not available. Policy Gradient agent will use simplified implementation.")
            return
        
        # Initialize policy network
        self.policy_network = PolicyNetwork(
            config.state_space_size,
            config.action_space_size,
            config.hidden_layers,
            config.dropout_rate
        ).to(self.device)
        
        # Initialize optimizer
        self.optimizer = optim.Adam(self.policy_network.parameters(), lr=config.learning_rate)
        
        # Episode memory
        self.episode_states = []
        self.episode_actions = []
        self.episode_rewards = []
    
    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """Select action using policy network"""
        if not TORCH_AVAILABLE:
            return np.random.randint(0, self.config.action_space_size)
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        action_probs = self.policy_network(state_tensor)
        
        if training:
            # Sample from distribution
            dist = Categorical(action_probs)
            action = dist.sample()
            return action.item()
        else:
            # Take most likely action
            return action_probs.argmax().item()
    
    def store_transition(self, state: np.ndarray, action: int, reward: float):
        """Store transition for episode"""
        self.episode_states.append(state)
        self.episode_actions.append(action)
        self.episode_rewards.append(reward)
    
    def train_episode(self) -> Optional[float]:
        """Train on completed episode"""
        if not TORCH_AVAILABLE or len(self.episode_states) == 0:
            return None
        
        # Calculate discounted rewards
        discounted_rewards = self._calculate_discounted_rewards()
        
        # Convert to tensors
        states = torch.FloatTensor(self.episode_states).to(self.device)
        actions = torch.LongTensor(self.episode_actions).to(self.device)
        rewards = torch.FloatTensor(discounted_rewards).to(self.device)
        
        # Normalize rewards
        rewards = (rewards - rewards.mean()) / (rewards.std() + 1e-8)
        
        # Calculate policy loss
        action_probs = self.policy_network(states)
        dist = Categorical(action_probs)
        log_probs = dist.log_prob(actions)
        
        policy_loss = -(log_probs * rewards).mean()
        
        # Optimize
        self.optimizer.zero_grad()
        policy_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_network.parameters(), 1.0)
        self.optimizer.step()
        
        # Clear episode memory
        self.episode_states = []
        self.episode_actions = []
        self.episode_rewards = []
        
        return policy_loss.item()
    
    def _calculate_discounted_rewards(self) -> List[float]:
        """Calculate discounted rewards for episode"""
        discounted_rewards = []
        running_reward = 0
        
        for reward in reversed(self.episode_rewards):
            running_reward = reward + self.config.gamma * running_reward
            discounted_rewards.insert(0, running_reward)
        
        return discounted_rewards

class RLTradingStrategy:
    """Main reinforcement learning trading strategy"""
    
    def __init__(self, config: RLConfig):
        self.config = config
        self.agent = None
        self.environment = None
        self.training_history = []
        self.performance_metrics = {}
        
        # Initialize agent based on algorithm
        if config.algorithm in [RLAlgorithm.DQN, RLAlgorithm.DOUBLE_DQN, RLAlgorithm.DUELING_DQN]:
            self.agent = DQNAgent(config)
        elif config.algorithm == RLAlgorithm.POLICY_GRADIENT:
            self.agent = PolicyGradientAgent(config)
        else:
            logging.warning(f"Algorithm {config.algorithm.value} not implemented. Using DQN.")
            self.agent = DQNAgent(config)
    
    def fit(self, data: pd.DataFrame, episodes: int = 1000) -> 'RLTradingStrategy':
        """Train the RL agent"""
        logging.info(f"Training RL strategy for {episodes} episodes...")
        
        # Initialize environment
        self.environment = TradingEnvironment(data, self.config)
        
        episode_rewards = []
        episode_losses = []
        
        for episode in range(episodes):
            # Reset environment
            state = self.environment.reset()
            episode_reward = 0
            episode_loss = 0
            step_count = 0
            
            while True:
                # Select action
                action = self.agent.select_action(state.features, training=True)
                
                # Execute action
                next_state, reward, done, info = self.environment.step(action)
                episode_reward += reward
                
                # Store transition
                if hasattr(self.agent, 'store_transition'):
                    if isinstance(self.agent, DQNAgent):
                        self.agent.store_transition(
                            state.features, action, reward, next_state.features, done
                        )
                    elif isinstance(self.agent, PolicyGradientAgent):
                        self.agent.store_transition(state.features, action, reward)
                
                # Train agent
                if isinstance(self.agent, DQNAgent) and step_count % self.config.training_frequency == 0:
                    loss = self.agent.train()
                    if loss is not None:
                        episode_loss += loss
                
                state = next_state
                step_count += 1
                
                if done:
                    break
            
            # Train policy gradient agent at end of episode
            if isinstance(self.agent, PolicyGradientAgent):
                loss = self.agent.train_episode()
                if loss is not None:
                    episode_loss = loss
            
            episode_rewards.append(episode_reward)
            episode_losses.append(episode_loss)
            
            # Log progress
            if episode % 100 == 0:
                avg_reward = np.mean(episode_rewards[-100:])
                avg_loss = np.mean(episode_losses[-100:]) if episode_losses[-100:] else 0
                logging.info(f"Episode {episode}: Avg Reward = {avg_reward:.4f}, Avg Loss = {avg_loss:.4f}")
        
        # Store training history
        self.training_history = {
            'episode_rewards': episode_rewards,
            'episode_losses': episode_losses
        }
        
        logging.info("RL strategy training completed")
        return self
    
    def predict(self, data: pd.DataFrame) -> TradingAction:
        """Generate trading action for current market state"""
        if self.environment is None:
            self.environment = TradingEnvironment(data, self.config)
        
        # Get current state
        state = self.environment._get_state()
        
        # Select action (no exploration)
        action_id = self.agent.select_action(state.features, training=False)
        
        # Map action ID to action type
        action_type = ActionType(action_id)
        
        # Calculate confidence and expected return (simplified)
        confidence = 0.7  # Placeholder
        expected_return = 0.01  # Placeholder
        risk_score = abs(state.position) * 0.5  # Placeholder
        
        # Determine position size based on action
        position_size_mapping = {
            ActionType.HOLD: 0.0,
            ActionType.BUY: 0.25,
            ActionType.SELL: -0.25,
            ActionType.BUY_STRONG: 0.5,
            ActionType.SELL_STRONG: -0.5
        }
        
        position_size = position_size_mapping.get(action_type, 0.0)
        
        return TradingAction(
            action_type=action_type,
            position_size=position_size,
            confidence=confidence,
            expected_return=expected_return,
            risk_score=risk_score,
            timestamp=datetime.now()
        )
    
    def evaluate(self, data: pd.DataFrame, episodes: int = 100) -> Dict[str, float]:
        """Evaluate strategy performance"""
        if self.environment is None:
            self.environment = TradingEnvironment(data, self.config)
        
        episode_returns = []
        episode_sharpe_ratios = []
        episode_max_drawdowns = []
        
        for episode in range(episodes):
            state = self.environment.reset()
            episode_portfolio_values = [self.environment.initial_balance]
            
            while True:
                action = self.agent.select_action(state.features, training=False)
                state, reward, done, info = self.environment.step(action)
                episode_portfolio_values.append(info['portfolio_value'])
                
                if done:
                    break
            
            # Calculate episode metrics
            portfolio_values = np.array(episode_portfolio_values)
            returns = np.diff(portfolio_values) / portfolio_values[:-1]
            
            total_return = (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0]
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            max_drawdown = np.max((np.maximum.accumulate(portfolio_values) - portfolio_values) / np.maximum.accumulate(portfolio_values))
            
            episode_returns.append(total_return)
            episode_sharpe_ratios.append(sharpe_ratio)
            episode_max_drawdowns.append(max_drawdown)
        
        # Calculate aggregate metrics
        self.performance_metrics = {
            'mean_return': np.mean(episode_returns),
            'std_return': np.std(episode_returns),
            'mean_sharpe_ratio': np.mean(episode_sharpe_ratios),
            'mean_max_drawdown': np.mean(episode_max_drawdowns),
            'win_rate': np.mean([r > 0 for r in episode_returns]),
            'best_return': np.max(episode_returns),
            'worst_return': np.min(episode_returns)
        }
        
        return self.performance_metrics

# Factory function for creating RL strategies
def create_rl_strategy(algorithm: RLAlgorithm = RLAlgorithm.DQN, 
                      config: Optional[RLConfig] = None) -> RLTradingStrategy:
    """Factory function to create RL trading strategy"""
    if config is None:
        config = RLConfig(algorithm=algorithm)
    else:
        config.algorithm = algorithm
    
    return RLTradingStrategy(config)

# Example usage and testing
if __name__ == "__main__":
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2020-01-01', periods=1000, freq='D')
    
    # Simulate price data with trends
    returns = np.random.normal(0.0005, 0.02, len(dates))
    # Add some trend periods
    returns[200:400] += 0.001  # Bull market
    returns[600:800] -= 0.002  # Bear market
    
    prices = 100 * np.exp(np.cumsum(returns))
    
    sample_data = pd.DataFrame({
        'close': prices,
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, len(prices)))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, len(prices)))),
        'open': prices + np.random.normal(0, 0.5, len(prices)),
        'volume': np.random.lognormal(10, 1, len(prices))
    }, index=dates)
    
    # Test RL strategy
    config = RLConfig(
        algorithm=RLAlgorithm.DQN,
        lookback_window=10,
        state_space_size=50,
        learning_rate=0.001,
        epsilon_decay=0.99
    )
    
    strategy = create_rl_strategy(RLAlgorithm.DQN, config)
    
    # Train strategy (small number of episodes for testing)
    strategy.fit(sample_data[:800], episodes=50)
    
    # Evaluate strategy
    metrics = strategy.evaluate(sample_data[800:], episodes=10)
    
    print("RL Strategy Performance:")
    for key, value in metrics.items():
        print(f"{key}: {value:.4f}")
    
    # Test prediction
    action = strategy.predict(sample_data[900:950])
    print(f"\nPredicted Action: {action.action_type.name}, Position Size: {action.position_size:.3f}")