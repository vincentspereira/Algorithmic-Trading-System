# Atomic Design Component Structure

This directory follows the **Atomic Design** methodology for organizing React components. This approach creates a clear hierarchy and promotes component reusability.

## Directory Structure

```
components/
├── atoms/              # Basic building blocks
│   ├── buttons/        # Button components
│   ├── inputs/         # Input field components
│   ├── labels/         # Label components
│   └── icons/          # Icon components
├── molecules/          # Groups of atoms
│   ├── form-groups/    # Form field combinations
│   ├── cards/          # Card components
│   └── navigation/     # Navigation components
├── organisms/          # Complex UI sections
│   ├── headers/        # Header components
│   └── sidebars/       # Sidebar components
├── templates/          # Page-level layouts
├── pages/              # Complete page components
└── [feature-specific]/ # Feature-based groupings
    ├── blockly/        # Visual strategy builder
    ├── charts/         # Trading charts
    ├── forms/          # Trading forms
    ├── grids/          # Data grids
    ├── layout/         # Layout components
    ├── predictions/    # AI predictions
    ├── risk-dashboard/ # Risk management
    ├── rl-optimization/# RL optimization
    └── strategy-builder/# Strategy building
```

## Component Hierarchy

### 🔗 Atoms
**Smallest functional units** - Basic HTML elements with styling
- Cannot be broken down further while maintaining functionality
- Examples: Button, Input, Label, Icon, Typography
- No business logic, pure presentation components

### 🧬 Molecules
**Simple groups of atoms** - Combine atoms for specific functions
- Contain minimal business logic
- Examples: SearchBox (Input + Button), FormField (Label + Input + ErrorMessage)
- Reusable across different contexts

### 🦠 Organisms
**Complex UI sections** - Combine molecules and atoms
- Contain business logic and state management
- Examples: Header (Logo + Navigation + SearchBox), ProductGrid (Multiple ProductCards)
- Form larger sections of interfaces

### 📄 Templates
**Page-level layouts** - Combine organisms to create page structures
- Define the overall layout without specific content
- Focus on content structure rather than content itself
- Examples: DashboardTemplate, TradingTemplate

### 🎯 Pages
**Complete page instances** - Specific instances of templates
- Contain actual content and data
- Connect to business logic and state management
- Examples: DashboardPage, TradingPage, StrategyBuilderPage

## Feature-Specific Components

For complex trading-specific functionality, components are organized by feature:

- **`blockly/`** - Visual strategy builder components using Blockly
- **`charts/`** - TradingView and custom chart components
- **`forms/`** - Trading-specific form components
- **`grids/`** - Data grid components for trading data
- **`predictions/`** - AI prediction display components
- **`risk-dashboard/`** - Risk management interface components
- **`strategy-builder/`** - Strategy creation and management components

## Component Naming Conventions

### Files
- Use PascalCase for component files: `Button.tsx`, `SearchBox.tsx`
- Use kebab-case for directories: `form-groups`, `risk-dashboard`
- Include `.stories.tsx` for Storybook stories
- Include `.test.tsx` for unit tests

### Components
- Use descriptive names that indicate purpose
- Prefix with context when needed: `TradingButton`, `ChartTooltip`
- Avoid generic names in favor of specific ones

## Import Guidelines

### Atoms and Molecules
```tsx
// Import from specific directories
import Button from '@/components/atoms/buttons/Button'
import FormField from '@/components/molecules/form-groups/FormField'
```

### Feature Components
```tsx
// Import from feature directories
import ChartContainer from '@/components/charts/ChartContainer'
import StrategyForm from '@/components/strategy-builder/StrategyForm'
```

### Index Files
Each directory should have an `index.ts` file for easier imports:
```tsx
// atoms/buttons/index.ts
export { default as Button } from './Button'
export { default as IconButton } from './IconButton'

// Usage
import { Button, IconButton } from '@/components/atoms/buttons'
```

## Best Practices

### 1. **Single Responsibility**
Each component should have one clear purpose and responsibility.

### 2. **Composition over Inheritance**
Use composition patterns to build complex components from simpler ones.

### 3. **Props Interface**
Always define TypeScript interfaces for component props:
```tsx
interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'small' | 'medium' | 'large'
  onClick: () => void
  children: React.ReactNode
}
```

### 4. **Consistent Styling**
- Use Tailwind CSS for styling consistency
- Define design tokens for colors, spacing, typography
- Create reusable style variants

### 5. **Accessibility**
- Include ARIA labels and roles
- Ensure keyboard navigation
- Maintain color contrast ratios
- Use semantic HTML elements

### 6. **Testing Strategy**
- Unit tests for atoms and molecules
- Integration tests for organisms
- E2E tests for pages and templates

## Migration Strategy

When refactoring existing components:

1. **Identify the atomic level** of each component
2. **Extract reusable parts** into atoms and molecules
3. **Maintain backward compatibility** during transition
4. **Update imports gradually** across the application
5. **Add documentation** for new component patterns

## Integration with Trading System

This structure supports the trading system's requirements:

- **Real-time data visualization** through chart organisms
- **Strategy building interface** through dedicated feature components
- **Risk management dashboards** through specialized organisms
- **Form handling** for trading operations through molecules
- **Consistent UI elements** through shared atoms

The Atomic Design structure ensures scalability, maintainability, and reusability across the entire trading application.