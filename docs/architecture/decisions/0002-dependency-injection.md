# ADR 0002: Dependency Injection Container

## Status
Accepted

## Context
The system has complex interdependencies between components:

- Event system depends on configuration
- Validation system depends on data sources and rules
- Trading strategies depend on indicators and risk managers
- All components need access to shared services (caching, logging, etc.)

Without dependency injection, components would be tightly coupled, making testing difficult and maintenance complex.

## Decision
Implement a **comprehensive dependency injection container** with the following features:

1. **Service Registration**: Register services with different lifetimes (singleton, transient, scoped)
2. **Automatic Resolution**: Resolve dependencies automatically based on type hints
3. **Lifecycle Management**: Manage service creation and disposal
4. **Circular Dependency Detection**: Prevent infinite loops in dependency chains
5. **Health Monitoring**: Track service health and performance
6. **Configuration Integration**: Support configuration-driven service instantiation

## Implementation Details

### Service Registration
```python
container = DependencyInjectionContainer()

# Register singleton service
container.register_singleton(DatabaseService, PostgresDatabase())

# Register transient service
container.register(TradingStrategy, MomentumStrategy)

# Register factory
container.register_factory(CacheManager, lambda: RedisCache(config))
```

### Service Resolution
```python
# Automatic dependency resolution
strategy = container.get_service(TradingStrategy)
# Container automatically resolves all dependencies
```

### Health Monitoring
```python
health_status = container.get_health_status()
metrics = container.get_metrics()
```

## Consequences

### Positive
- **Loose Coupling**: Components don't create their own dependencies
- **Testability**: Easy to inject mock dependencies for testing
- **Maintainability**: Changes to service implementations don't affect consumers
- **Flexibility**: Services can be swapped without code changes
- **Performance Monitoring**: Built-in metrics and health checks

### Negative
- **Complexity**: Additional abstraction layer
- **Runtime Overhead**: Service resolution adds small performance cost
- **Configuration Complexity**: Need to configure service registrations

### Mitigation
- Use type hints for automatic resolution
- Provide sensible defaults for common services
- Implement lazy loading for expensive services
- Cache resolved service instances

## Related ADRs
- ADR 0001: Layered Architecture Pattern
- ADR 0004: Plugin Architecture