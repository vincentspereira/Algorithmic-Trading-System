import { useEffect, useState } from 'react'
import {
  Box,
  Container,
  Grid,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  CircularProgress,
} from '@mui/material'
import {
  Timeline,
  Warning,
  CheckCircle,
  Error,
} from '@mui/icons-material'
import { Line } from 'react-chartjs-2'
import axios from 'axios'

// Types
interface DependencyHealth {
  name: string
  version: string
  tier: number
  last_updated: string
  status: string
  vulnerabilities: any[]
  updates_available: boolean
  performance_metrics: {
    uptime: number
    response_time: number
    error_rate: number
  }
}

export default function Dashboard() {
  const [dependencies, setDependencies] = useState<DependencyHealth[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchDependencies()
    // Set up polling every 5 minutes
    const interval = setInterval(fetchDependencies, 300000)
    return () => clearInterval(interval)
  }, [])

  const fetchDependencies = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/dependencies/health')
      setDependencies(response.data)
      setLoading(false)
    } catch (err) {
      setError('Failed to fetch dependency data')
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle color="success" />
      case 'warning':
        return <Warning color="warning" />
      case 'critical':
        return <Error color="error" />
      default:
        return <Timeline />
    }
  }

  const getTierColor = (tier: number) => {
    switch (tier) {
      case 1:
        return 'error'
      case 2:
        return 'warning'
      case 3:
        return 'info'
      case 4:
        return 'default'
      default:
        return 'default'
    }
  }

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
      >
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
      >
        <Typography color="error">{error}</Typography>
      </Box>
    )
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Dependency Health Dashboard
      </Typography>

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={3}>
          <Paper
            sx={{
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <Typography variant="h6">Total Dependencies</Typography>
            <Typography variant="h3">{dependencies.length}</Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={3}>
          <Paper
            sx={{
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <Typography variant="h6">Healthy</Typography>
            <Typography variant="h3" color="success.main">
              {dependencies.filter((d) => d.status === 'healthy').length}
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={3}>
          <Paper
            sx={{
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <Typography variant="h6">Updates Available</Typography>
            <Typography variant="h3" color="warning.main">
              {dependencies.filter((d) => d.updates_available).length}
            </Typography>
          </Paper>
        </Grid>
        <Grid item xs={12} md={3}>
          <Paper
            sx={{
              p: 2,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
            }}
          >
            <Typography variant="h6">Vulnerabilities</Typography>
            <Typography variant="h3" color="error.main">
              {dependencies.reduce(
                (acc, d) => acc + d.vulnerabilities.length,
                0
              )}
            </Typography>
          </Paper>
        </Grid>
      </Grid>

      {/* Dependencies Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Version</TableCell>
              <TableCell>Tier</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Last Updated</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {dependencies.map((dep) => (
              <TableRow key={dep.name}>
                <TableCell>{dep.name}</TableCell>
                <TableCell>{dep.version}</TableCell>
                <TableCell>
                  <Chip
                    label={`Tier ${dep.tier}`}
                    color={getTierColor(dep.tier)}
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Box display="flex" alignItems="center" gap={1}>
                    {getStatusIcon(dep.status)}
                    {dep.status}
                  </Box>
                </TableCell>
                <TableCell>
                  {new Date(dep.last_updated).toLocaleString()}
                </TableCell>
                <TableCell>
                  <Button
                    variant="contained"
                    size="small"
                    onClick={() => {
                      // Handle viewing details
                    }}
                  >
                    View Details
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Container>
  )
}
