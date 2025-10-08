import { useState } from 'react'
import { Box, Drawer, Button, Typography, Avatar, Divider, CircularProgress } from '@mui/material'
import { Login as LoginIcon, Dashboard as DashboardIcon, Person as PersonIcon, Logout as LogoutIcon } from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/store'
import { authService } from '@/api/services/auth.service'

interface LandingSidebarProps {
  open: boolean
  onClose: () => void
  variant?: 'temporary' | 'permanent'
}

export default function LandingSidebar({ open, onClose, variant = 'temporary' }: LandingSidebarProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { user, isAuthenticated, clearAuth } = useAuthStore()
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  const handleLoginClick = () => {
    navigate('/login')
    onClose()
  }

  const handleDashboardClick = () => {
    navigate('/dashboard')
    onClose()
  }

  const handleLogout = async () => {
    setIsLoggingOut(true)
    try {
      await authService.logout()
      // Очищаем auth только при успешном logout
      clearAuth()
      navigate('/')
      onClose()
    } catch (error) {
      console.error('Logout error:', error)
      // Показываем ошибку пользователю
      alert(t('auth:logout_error'))
    } finally {
      setIsLoggingOut(false)
    }
  }

  const drawerContent = (
    <Box
      sx={{
        width: { xs: '85vw', sm: 320, md: 360 },
        maxWidth: 400,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'background.paper',
        p: { xs: 2, sm: 3 },
      }}
    >
      <Typography 
        variant="h6" 
        sx={{ 
          mb: 3, 
          fontWeight: 700,
          fontSize: { xs: '1.125rem', sm: '1.25rem' }
        }}
      >
        {t('common:app_name')}
      </Typography>

      <Divider sx={{ mb: 3 }} />

      {!isAuthenticated ? (
        // Неавторизованный пользователь
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Typography 
            variant="body2" 
            color="text.secondary" 
            sx={{ 
              mb: 2,
              fontSize: { xs: '0.875rem', sm: '1rem' }
            }}
          >
            {t('landing:sidebar_guest_text')}
          </Typography>
          <Button
            variant="contained"
            size="large"
            startIcon={<LoginIcon />}
            onClick={handleLoginClick}
            fullWidth
            sx={{
              background: 'linear-gradient(135deg, #00897B 0%, #00695C 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #00695C 0%, #00897B 100%)',
              },
            }}
          >
            {t('landing:login_button')}
          </Button>
        </Box>
      ) : (
        // Авторизованный пользователь
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Avatar sx={{ 
              bgcolor: 'primary.main', 
              width: { xs: 48, sm: 56 }, 
              height: { xs: 48, sm: 56 } 
            }}>
              <PersonIcon />
            </Avatar>
            <Box>
              <Typography variant="body2" color="text.secondary">
                {t('landing:welcome')}
              </Typography>
              <Typography variant="h6" fontWeight={600}>
                {user?.username}
              </Typography>
            </Box>
          </Box>

          <Divider sx={{ my: 1 }} />

          <Button
            variant="contained"
            size="large"
            startIcon={<DashboardIcon />}
            onClick={handleDashboardClick}
            fullWidth
            sx={{
              background: 'linear-gradient(135deg, #00897B 0%, #00695C 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #00695C 0%, #00897B 100%)',
              },
            }}
          >
            {t('landing:cabinet_button')}
          </Button>

          <Button
            variant="outlined"
            size="large"
            startIcon={isLoggingOut ? <CircularProgress size={20} color="inherit" /> : <LogoutIcon />}
            onClick={handleLogout}
            disabled={isLoggingOut}
            fullWidth
            sx={{
              borderColor: '#dc2626',
              color: '#dc2626',
              borderWidth: 2,
              '&:hover': {
                borderColor: '#b91c1c',
                bgcolor: 'rgba(220, 38, 38, 0.04)',
                borderWidth: 2,
              },
              '&.Mui-disabled': {
                borderColor: 'rgba(220, 38, 38, 0.3)',
                color: 'rgba(220, 38, 38, 0.3)',
              },
            }}
          >
            {isLoggingOut ? t('common:loading') : t('auth:logout')}
          </Button>
        </Box>
      )}

      <Box sx={{ flexGrow: 1 }} />

      <Divider sx={{ mb: 2 }} />

      <Typography variant="caption" color="text.secondary" textAlign="center">
        © 2025 Everis
      </Typography>
    </Box>
  )

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      variant={variant}
      sx={{
        '& .MuiDrawer-paper': {
          boxSizing: 'border-box',
        },
      }}
    >
      {drawerContent}
    </Drawer>
  )
}
