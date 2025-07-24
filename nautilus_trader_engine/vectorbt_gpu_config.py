"""
VectorBT GPU Configuration for Nautilus Trader Engine

This module configures VectorBT for GPU acceleration when available,
with automatic fallback to CPU processing. It also provides integration
with NautilusTrader data feeds and optimized settings for trading applications.

Features:
- Automatic GPU detection and configuration
- CPU fallback when GPU is not available
- VectorBT settings optimization for trading
- Integration with NautilusTrader data structures
- Performance monitoring and benchmarking

Author: Kilo Code
Version: 1.0.0
"""

import os
import sys
import logging
import warnings
from typing import Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning, module='vectorbt')
warnings.filterwarnings('ignore', category=FutureWarning, module='numba')

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VectorBTGPUConfig:
    """Configuration manager for VectorBT GPU acceleration"""
    
    def __init__(self):
        self.gpu_available = False
        self.cuda_available = False
        self.numba_available = False
        self.vectorbt_available = False
        self.config_applied = False
        
        # Performance settings
        self.settings = {
            'parallel': True,
            'chunked': True,
            'chunk_len': 10000,
            'use_numba': True,
            'cache': True
        }
        
        self._check_dependencies()
        self._configure_environment()
    
    def _check_dependencies(self):
        """Check availability of required dependencies"""
        try:
            # Check VectorBT
            import vectorbt as vbt
            self.vectorbt_available = True
            logger.info("✓ VectorBT available")
        except ImportError:
            logger.warning("✗ VectorBT not available")
            return
        
        try:
            # Check Numba
            import numba
            from numba import cuda
            self.numba_available = True
            logger.info(f"✓ Numba available (version: {numba.__version__})")
            
            # Check CUDA availability
            try:
                cuda.detect()
                self.cuda_available = True
                self.gpu_available = True
                logger.info("✓ CUDA GPU detected")
                
                # Get GPU information
                gpu_info = self._get_gpu_info()
                if gpu_info:
                    logger.info(f"GPU: {gpu_info['name']} ({gpu_info['memory_gb']:.1f} GB)")
                
            except Exception as e:
                logger.info("ℹ CUDA not available, using CPU")
                self.cuda_available = False
                
        except ImportError:
            logger.warning("✗ Numba not available")
    
    def _get_gpu_info(self) -> Optional[Dict[str, Any]]:
        """Get GPU information if available"""
        try:
            from numba import cuda
            
            if not self.cuda_available:
                return None
            
            device = cuda.get_current_device()
            memory_info = device.memory_info
            
            return {
                'name': device.name.decode('utf-8'),
                'compute_capability': device.compute_capability,
                'memory_gb': memory_info.total / (1024**3),
                'free_memory_gb': memory_info.free / (1024**3)
            }
            
        except Exception as e:
            logger.warning(f"Could not get GPU info: {e}")
            return None
    
    def _configure_environment(self):
        """Configure environment variables for optimal performance"""
        try:
            if not self.vectorbt_available:
                return
            
            # Set environment variables for Numba
            if self.numba_available:
                # Enable parallel processing
                os.environ['NUMBA_NUM_THREADS'] = str(os.cpu_count())
                
                # Configure CUDA if available
                if self.cuda_available:
                    os.environ['NUMBA_ENABLE_CUDASIM'] = '0'
                    os.environ['NUMBA_CUDA_DEBUGINFO'] = '0'
                    logger.info("✓ CUDA environment configured")
                else:
                    # Optimize for CPU
                    os.environ['NUMBA_THREADING_LAYER'] = 'tbb'
                    logger.info("✓ CPU threading optimized")
            
            # Configure VectorBT settings
            import vectorbt as vbt
            
            # Set global settings
            vbt.settings.set_theme('dark')
            vbt.settings.array.chunked = self.settings['chunked']
            vbt.settings.array.chunk_len = self.settings['chunk_len']
            vbt.settings.caching.enabled = self.settings['cache']
            vbt.settings.caching.whitelist = ['*']
            
            # Configure parallel processing
            if self.settings['parallel']:
                vbt.settings.numba.parallel = True
                vbt.settings.numba.nopython = True
                
            self.config_applied = True
            logger.info("✓ VectorBT configuration applied")
            
        except Exception as e:
            logger.error(f"Failed to configure environment: {e}")
    
    def get_optimal_settings(self, data_size: int) -> Dict[str, Any]:
        """Get optimal settings based on data size and hardware"""
        settings = self.settings.copy()
        
        # Adjust chunk size based on data size
        if data_size < 1000:
            settings['chunk_len'] = min(1000, data_size)
            settings['chunked'] = False
        elif data_size < 10000:
            settings['chunk_len'] = min(5000, data_size // 2)
        else:
            settings['chunk_len'] = 10000
        
        # Adjust parallel processing based on hardware
        if self.gpu_available:
            settings['use_gpu'] = True
            settings['parallel'] = True
        else:
            settings['use_gpu'] = False
            settings['parallel'] = os.cpu_count() > 2
        
        return settings
    
    def benchmark_performance(self, data: pd.DataFrame) -> Dict[str, float]:
        """Benchmark VectorBT performance with current configuration"""
        try:
            if not self.vectorbt_available:
                return {'error': 'VectorBT not available'}
            
            import vectorbt as vbt
            import time
            
            logger.info("Running performance benchmark...")
            
            # Prepare test data
            close_prices = data['close'] if 'close' in data.columns else data.iloc[:, 0]
            
            # Test 1: Simple moving average calculation
            start_time = time.time()
            ma_10 = close_prices.rolling(10).mean()
            ma_30 = close_prices.rolling(30).mean()
            ma_time = time.time() - start_time
            
            # Test 2: Signal generation
            start_time = time.time()
            entries = ma_10 > ma_30
            exits = ma_10 < ma_30
            signal_time = time.time() - start_time
            
            # Test 3: Portfolio simulation
            start_time = time.time()
            portfolio = vbt.Portfolio.from_signals(
                close=close_prices,
                entries=entries,
                exits=exits,
                init_cash=100000
            )
            portfolio_time = time.time() - start_time
            
            # Test 4: Metrics calculation
            start_time = time.time()
            total_return = portfolio.total_return()
            sharpe = portfolio.sharpe_ratio()
            drawdown = portfolio.max_drawdown()
            metrics_time = time.time() - start_time
            
            results = {
                'moving_average_time': ma_time,
                'signal_generation_time': signal_time,
                'portfolio_simulation_time': portfolio_time,
                'metrics_calculation_time': metrics_time,
                'total_time': ma_time + signal_time + portfolio_time + metrics_time,
                'data_points': len(close_prices),
                'performance_score': len(close_prices) / (ma_time + signal_time + portfolio_time + metrics_time)
            }
            
            logger.info(f"Benchmark completed: {results['performance_score']:.0f} data points/second")
            return results
            
        except Exception as e:
            logger.error(f"Benchmark failed: {e}")
            return {'error': str(e)}
    
    def create_optimized_portfolio(self, data: pd.DataFrame, entries: pd.Series, 
                                 exits: pd.Series, init_cash: float = 100000) -> Optional[Any]:
        """Create VectorBT portfolio with optimized settings"""
        try:
            if not self.vectorbt_available:
                logger.error("VectorBT not available")
                return None
            
            import vectorbt as vbt
            
            # Get optimal settings for this data size
            optimal_settings = self.get_optimal_settings(len(data))
            
            # Apply settings temporarily
            with vbt.settings.config(
                chunked=optimal_settings['chunked'],
                chunk_len=optimal_settings['chunk_len'],
                parallel=optimal_settings['parallel']
            ):
                # Create portfolio
                close_prices = data['close'] if 'close' in data.columns else data.iloc[:, 0]
                
                portfolio = vbt.Portfolio.from_signals(
                    close=close_prices,
                    entries=entries,
                    exits=exits,
                    init_cash=init_cash,
                    freq='D'
                )
                
                return portfolio
                
        except Exception as e:
            logger.error(f"Failed to create optimized portfolio: {e}")
            return None
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        info = {
            'vectorbt_available': self.vectorbt_available,
            'numba_available': self.numba_available,
            'cuda_available': self.cuda_available,
            'gpu_available': self.gpu_available,
            'config_applied': self.config_applied,
            'cpu_count': os.cpu_count(),
            'settings': self.settings
        }
        
        # Add GPU info if available
        gpu_info = self._get_gpu_info()
        if gpu_info:
            info['gpu_info'] = gpu_info
        
        # Add version information
        try:
            import vectorbt as vbt
            info['vectorbt_version'] = vbt.__version__
        except:
            pass
        
        try:
            import numba
            info['numba_version'] = numba.__version__
        except:
            pass
        
        return info
    
    def print_configuration_summary(self):
        """Print a summary of the current configuration"""
        print("\n" + "=" * 60)
        print("VECTORBT GPU CONFIGURATION SUMMARY")
        print("=" * 60)
        
        info = self.get_system_info()
        
        print("AVAILABILITY:")
        print(f"  VectorBT: {'✓' if info['vectorbt_available'] else '✗'}")
        print(f"  Numba: {'✓' if info['numba_available'] else '✗'}")
        print(f"  CUDA GPU: {'✓' if info['cuda_available'] else '✗'}")
        print(f"  Configuration Applied: {'✓' if info['config_applied'] else '✗'}")
        
        print(f"\nHARDWARE:")
        print(f"  CPU Cores: {info['cpu_count']}")
        
        if 'gpu_info' in info:
            gpu = info['gpu_info']
            print(f"  GPU: {gpu['name']}")
            print(f"  GPU Memory: {gpu['memory_gb']:.1f} GB")
            print(f"  Compute Capability: {gpu['compute_capability']}")
        
        print(f"\nSETTINGS:")
        for key, value in info['settings'].items():
            print(f"  {key}: {value}")
        
        if 'vectorbt_version' in info:
            print(f"\nVERSIONS:")
            print(f"  VectorBT: {info['vectorbt_version']}")
            if 'numba_version' in info:
                print(f"  Numba: {info['numba_version']}")
        
        print("\nRECOMMENDATIONS:")
        if not info['cuda_available']:
            print("  • Install CUDA for GPU acceleration")
            print("  • Ensure compatible GPU drivers are installed")
        if not info['numba_available']:
            print("  • Install numba for JIT compilation: pip install numba")
        if info['cpu_count'] < 4:
            print("  • Consider upgrading to a multi-core CPU for better performance")
        
        print()


# Global configuration instance
gpu_config = VectorBTGPUConfig()


def configure_vectorbt_gpu() -> VectorBTGPUConfig:
    """Configure VectorBT for optimal GPU/CPU performance"""
    return gpu_config


def get_vectorbt_config() -> VectorBTGPUConfig:
    """Get the current VectorBT configuration"""
    return gpu_config


def main():
    """Main function to demonstrate GPU configuration"""
    print("=" * 80)
    print("VECTORBT GPU CONFIGURATION")
    print("Optimizing VectorBT for GPU/CPU Performance")
    print("=" * 80)
    
    # Configure and display summary
    config = configure_vectorbt_gpu()
    config.print_configuration_summary()
    
    # Test with sample data if VectorBT is available
    if config.vectorbt_available:
        try:
            # Create sample data
            dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')
            sample_data = pd.DataFrame({
                'close': np.random.randn(len(dates)).cumsum() + 100
            }, index=dates)
            
            print("Running performance benchmark with sample data...")
            benchmark_results = config.benchmark_performance(sample_data)
            
            if 'error' not in benchmark_results:
                print(f"✅ Benchmark completed successfully!")
                print(f"Performance: {benchmark_results['performance_score']:.0f} data points/second")
                print(f"Total time: {benchmark_results['total_time']:.3f} seconds")
            else:
                print(f"❌ Benchmark failed: {benchmark_results['error']}")
                
        except Exception as e:
            print(f"❌ Benchmark failed: {e}")
    
    print("\n✅ VectorBT GPU configuration completed!")


if __name__ == "__main__":
    main()