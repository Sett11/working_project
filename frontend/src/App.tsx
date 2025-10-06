import { Box, Container, Typography, Button, Stack, Paper } from '@mui/material'
import { Logout as LogoutIcon } from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useUIStore, useAuthStore } from './store'
import { authService } from './api/services/auth.service'

function App() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { theme, toggleTheme, language, setLanguage } = useUIStore()
  const { user, clearAuth } = useAuthStore()

  const handleLogout = async () => {
    try {
      await authService.logout()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      clearAuth()
      navigate('/login')
    }
  }

  return (
    <Container maxWidth="lg">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 4,
          py: 4,
          bgcolor: 'background.default',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            maxWidth: 800,
            width: '100%',
            textAlign: 'center',
          }}
        >
          <Typography variant="h2" component="h1" gutterBottom>
            {t('common:app_name')}
          </Typography>

          <Typography variant="h4" color="primary" gutterBottom>
            {t('common:welcome')}, {user?.username}!
          </Typography>

          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Вы успешно вошли в систему
          </Typography>

          <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
            <Button variant="contained" onClick={toggleTheme}>
              Toggle Theme (Current: {theme})
            </Button>

            <Button
              variant="outlined"
              onClick={() => setLanguage(language === 'ru' ? 'en' : 'ru')}
            >
              Language: {language.toUpperCase()}
            </Button>
          </Stack>

          <Button
            variant="contained"
            color="error"
            startIcon={<LogoutIcon />}
            onClick={handleLogout}
            size="large"
          >
            {t('auth:logout')}
          </Button>

          <Typography variant="body2" color="text.secondary" sx={{ mt: 4 }}>
            ✅ Frontend инфраструктура настроена<br />
            React + TypeScript + MUI + Zustand + TanStack Query + i18n
          </Typography>
        </Paper>
      </Box>
    </Container>
  )
}

export default App
