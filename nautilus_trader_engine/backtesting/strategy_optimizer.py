"""
Strategy Optimizer for Backtesting

This module provides optimization capabilities for trading strategies
including parameter optimization and walk-forward optimization.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime
import logging
import random

from .base import BacktestEngine, BacktestResult

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    """Result of strategy optimization"""
    best_parameters: Dict[str, Any]
    best_fitness: float
    optimization_history: List[Dict[str, Any]]
    convergence_achieved: bool
    total_evaluations: int
    optimization_time_seconds: float


class StrategyOptimizer:
    """Strategy optimization engine"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.optimization_method = config.get('optimization_method', 'grid_search')
        self.objective_function = config.get('objective_function', 'sharpe_ratio')
        self.constraints = config.get('constraints', {})
        
        # Genetic algorithm parameters
        self.population_size = config.get('population_size', 50)
        self.generations = config.get('generations', 100)
        self.mutation_rate = config.get('mutation_rate', 0.1)
        self.crossover_rate = config.get('crossover_rate', 0.8)
        
        logger.info(f"StrategyOptimizer initialized with method: {self.optimization_method}")
    
    def optimize(self, parameter_space: Dict[str, Dict[str, Any]], 
                 strategy_class: Any, 
                 data: pd.DataFrame,
                 engine_class: type = BacktestEngine) -> OptimizationResult:
        """Optimize strategy parameters"""
        
        if self.optimization_method == 'genetic_algorithm':
            return self._genetic_algorithm_optimize(parameter_space, strategy_class, data, engine_class)
        elif self.optimization_method == 'grid_search':
            return self._grid_search_optimize(parameter_space, strategy_class, data, engine_class)
        elif self.optimization_method == 'random_search':
            return self._random_search_optimize(parameter_space, strategy_class, data, engine_class)
        else:
            raise ValueError(f"Unknown optimization method: {self.optimization_method}")
    
    def _genetic_algorithm_optimize(self, parameter_space: Dict[str, Dict[str, Any]], 
                                   strategy_class: Any, 
                                   data: pd.DataFrame,
                                   engine_class: type) -> OptimizationResult:
        """Genetic algorithm optimization"""
        logger.info("Starting genetic algorithm optimization...")
        
        # Initialize population
        population = self._initialize_population(parameter_space)
        best_fitness = float('-inf')
        best_parameters = {}
        history = []
        evaluations = 0
        
        for generation in range(self.generations):
            # Evaluate fitness
            fitness_scores = []
            for individual in population:
                try:
                    engine = engine_class(self.config.get('initial_capital', 100000))
                    engine.add_strategy(strategy_class, **individual)
                    engine.add_data(data, "OPTIMIZATION")
                    result = engine.run()
                    
                    fitness = self._calculate_fitness(result)
                    fitness_scores.append((individual, fitness))
                    evaluations += 1
                    
                    if fitness > best_fitness:
                        best_fitness = fitness
                        best_parameters = individual.copy()
                except Exception as e:
                    logger.warning(f"Failed to evaluate individual: {e}")
                    fitness_scores.append((individual, float('-inf')))
            
            # Sort by fitness
            fitness_scores.sort(key=lambda x: x[1], reverse=True)
            history.append({
                'generation': generation,
                'best_fitness': fitness_scores[0][1],
                'avg_fitness': np.mean([score[1] for score in fitness_scores]),
                'worst_fitness': fitness_scores[-1][1]
            })
            
            # Check convergence
            if generation > 10 and abs(history[-1]['best_fitness'] - history[-10]['best_fitness']) < 0.001:
                logger.info("Convergence achieved")
                break
            
            # Create new generation
            new_population = []
            
            # Elitism - keep best individuals
            elite_count = max(1, self.population_size // 10)
            for i in range(elite_count):
                new_population.append(fitness_scores[i][0].copy())
            
            # Generate offspring
            while len(new_population) < self.population_size:
                parent1 = self._tournament_selection(fitness_scores)
                parent2 = self._tournament_selection(fitness_scores)
                
                if random.random() < self.crossover_rate:
                    child = self._crossover(parent1, parent2, parameter_space)
                else:
                    child = parent1.copy()
                
                if random.random() < self.mutation_rate:
                    child = self._mutate(child, parameter_space)
                
                new_population.append(child)
            
            population = new_population
        
        convergence = len(history) < self.generations
        logger.info(f"Optimization completed. Best fitness: {best_fitness:.4f}")
        
        return OptimizationResult(
            best_parameters=best_parameters,
            best_fitness=best_fitness,
            optimization_history=history,
            convergence_achieved=convergence,
            total_evaluations=evaluations,
            optimization_time_seconds=0.0  # Would be set in real implementation
        )
    
    def _initialize_population(self, parameter_space: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Initialize population for genetic algorithm"""
        population = []
        for _ in range(self.population_size):
            individual = {}
            for param_name, param_config in parameter_space.items():
                param_type = param_config['type']
                param_min = param_config['min']
                param_max = param_config['max']
                
                if param_type == 'int':
                    individual[param_name] = random.randint(param_min, param_max)
                elif param_type == 'float':
                    individual[param_name] = random.uniform(param_min, param_max)
                else:
                    individual[param_name] = param_min  # Default case
            
            population.append(individual)
        return population
    
    def _tournament_selection(self, fitness_scores: List[tuple]) -> Dict[str, Any]:
        """Tournament selection for genetic algorithm"""
        tournament_size = 3
        tournament = random.sample(fitness_scores, min(tournament_size, len(fitness_scores)))
        tournament.sort(key=lambda x: x[1], reverse=True)
        return tournament[0][0].copy()
    
    def _crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any], 
                   parameter_space: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Crossover operation for genetic algorithm"""
        child = {}
        for param_name in parent1:
            if random.random() < 0.5:
                child[param_name] = parent1[param_name]
            else:
                child[param_name] = parent2[param_name]
        return child
    
    def _mutate(self, individual: Dict[str, Any], 
                parameter_space: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Mutation operation for genetic algorithm"""
        for param_name, param_config in parameter_space.items():
            if random.random() < 0.1:  # 10% mutation rate per parameter
                param_type = param_config['type']
                param_min = param_config['min']
                param_max = param_config['max']
                
                if param_type == 'int':
                    individual[param_name] = random.randint(param_min, param_max)
                elif param_type == 'float':
                    individual[param_name] = random.uniform(param_min, param_max)
        return individual
    
    def _grid_search_optimize(self, parameter_space: Dict[str, Dict[str, Any]], 
                             strategy_class: Any, 
                             data: pd.DataFrame,
                             engine_class: type) -> OptimizationResult:
        """Grid search optimization"""
        logger.info("Starting grid search optimization...")
        # Simplified implementation - would need to generate parameter combinations
        return self._random_search_optimize(parameter_space, strategy_class, data, engine_class)
    
    def _random_search_optimize(self, parameter_space: Dict[str, Dict[str, Any]], 
                               strategy_class: Any, 
                               data: pd.DataFrame,
                               engine_class: type) -> OptimizationResult:
        """Random search optimization"""
        logger.info("Starting random search optimization...")
        # Simplified implementation
        best_fitness = float('-inf')
        best_parameters = {}
        history = []
        evaluations = 0
        max_evaluations = 100
        
        for i in range(max_evaluations):
            # Generate random parameters
            parameters = {}
            for param_name, param_config in parameter_space.items():
                param_type = param_config['type']
                param_min = param_config['min']
                param_max = param_config['max']
                
                if param_type == 'int':
                    parameters[param_name] = random.randint(param_min, param_max)
                elif param_type == 'float':
                    parameters[param_name] = random.uniform(param_min, param_max)
                else:
                    parameters[param_name] = param_min
            
            try:
                engine = engine_class(self.config.get('initial_capital', 100000))
                engine.add_strategy(strategy_class, **parameters)
                engine.add_data(data, "OPTIMIZATION")
                result = engine.run()
                
                fitness = self._calculate_fitness(result)
                evaluations += 1
                
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_parameters = parameters.copy()
                
                history.append({
                    'evaluation': i,
                    'fitness': fitness,
                    'parameters': parameters.copy()
                })
            except Exception as e:
                logger.warning(f"Failed to evaluate parameters: {e}")
                history.append({
                    'evaluation': i,
                    'fitness': float('-inf'),
                    'parameters': parameters.copy()
                })
        
        return OptimizationResult(
            best_parameters=best_parameters,
            best_fitness=best_fitness,
            optimization_history=history,
            convergence_achieved=False,
            total_evaluations=evaluations,
            optimization_time_seconds=0.0
        )
    
    def _calculate_fitness(self, result: BacktestResult) -> float:
        """Calculate fitness based on objective function"""
        if self.objective_function == 'sharpe_ratio':
            return result.sharpe_ratio if result.sharpe_ratio is not None else 0.0
        elif self.objective_function == 'total_return':
            return result.total_return if result.total_return is not None else 0.0
        elif self.objective_function == 'profit_factor':
            return result.profit_factor if result.profit_factor is not None else 0.0
        elif self.objective_function == 'calmar_ratio':
            return result.calmar_ratio if result.calmar_ratio is not None else 0.0
        else:
            return result.sharpe_ratio if result.sharpe_ratio is not None else 0.0
    
    def walk_forward_optimize(self, parameter_space: Dict[str, Dict[str, Any]], 
                             strategy_class: Any,
                             data: pd.DataFrame,
                             window_size_months: int = 12,
                             step_size_months: int = 3) -> Dict[str, Any]:
        """Walk-forward optimization"""
        logger.info("Starting walk-forward optimization...")
        
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Data must have datetime index for walk-forward optimization")
        
        # Sort data by date
        data = data.sort_index()
        
        # Calculate periods
        start_date = data.index[0]
        end_date = data.index[-1]
        
        periods = []
        current_start = start_date
        
        while current_start < end_date:
            # Training period
            training_end = current_start + pd.DateOffset(months=window_size_months)
            training_data = data[(data.index >= current_start) & (data.index < training_end)]
            
            if len(training_data) < 30:  # Minimum data requirement
                break
            
            # Test period
            test_start = training_end
            test_end = test_start + pd.DateOffset(months=step_size_months)
            test_data = data[(data.index >= test_start) & (data.index < test_end)]
            
            if len(test_data) < 10:  # Minimum test data requirement
                break
            
            # Optimize on training data
            try:
                optimization_result = self.optimize(parameter_space, strategy_class, training_data)
                
                # Test on test data with optimized parameters
                engine = BacktestEngine(self.config.get('initial_capital', 100000))
                engine.add_strategy(strategy_class, **optimization_result.best_parameters)
                engine.add_data(test_data, "WALK_FORWARD")
                test_result = engine.run()
                
                periods.append({
                    'period': f"{current_start.strftime('%Y-%m')} to {test_end.strftime('%Y-%m')}",
                    'training_period': f"{current_start.strftime('%Y-%m')} to {training_end.strftime('%Y-%m')}",
                    'test_period': f"{test_start.strftime('%Y-%m')} to {test_end.strftime('%Y-%m')}",
                    'optimal_parameters': optimization_result.best_parameters,
                    'in_sample_performance': {
                        'sharpe_ratio': optimization_result.best_fitness,
                        'return': 0.0  # Would be calculated from training results
                    },
                    'out_of_sample_performance': {
                        'sharpe_ratio': test_result.sharpe_ratio,
                        'return': test_result.total_return
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to optimize period {current_start}: {e}")
            
            current_start = current_start + pd.DateOffset(months=step_size_months)
        
        # Calculate overall performance
        if periods:
            avg_in_sample_sharpe = np.mean([
                p['in_sample_performance']['sharpe_ratio'] for p in periods
                if p['in_sample_performance']['sharpe_ratio'] is not None
            ])
            avg_out_of_sample_sharpe = np.mean([
                p['out_of_sample_performance']['sharpe_ratio'] for p in periods
                if p['out_of_sample_performance']['sharpe_ratio'] is not None
            ])
            
            performance_degradation = avg_in_sample_sharpe - avg_out_of_sample_sharpe \
                if avg_in_sample_sharpe is not None and avg_out_of_sample_sharpe is not None else 0
            
            overall_performance = {
                'avg_in_sample_sharpe': avg_in_sample_sharpe,
                'avg_out_of_sample_sharpe': avg_out_of_sample_sharpe,
                'performance_degradation': performance_degradation,
                'parameter_stability': 0.75  # Placeholder
            }
        else:
            overall_performance = {
                'avg_in_sample_sharpe': 0.0,
                'avg_out_of_sample_sharpe': 0.0,
                'performance_degradation': 0.0,
                'parameter_stability': 0.0
            }
        
        return {
            'periods': periods,
            'overall_performance': overall_performance
        }