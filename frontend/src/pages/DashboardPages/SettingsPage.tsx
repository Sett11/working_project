import { Box, Typography, Paper, Alert, CircularProgress } from '@mui/material'
import { Settings as SettingsIcon } from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/store'
import { Navigate } from 'react-router-dom'

export default function SettingsPage() {
  const { t } = useTranslation()
  const { user, isAuthInitialized } = useAuthStore()

  // Показываем загрузку, пока аутентификация инициализируется
  if (!isAuthInitialized) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '400px',
        }}
      >
        <CircularProgress />
      </Box>
    )
  }

  // Проверка прав администратора после завершения загрузки
  if (!user?.is_admin) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <SettingsIcon sx={{ fontSize: 40, mr: 2, color: 'primary.main' }} />
        <Typography variant="h4" component="h1" fontWeight={700}>
          {t('dashboard:settings_page_title')}
        </Typography>
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        {t('dashboard:admin_only')}
      </Alert>

      <Paper elevation={2} sx={{ p: 4, borderRadius: 3 }}>
        <Typography variant="h6" gutterBottom fontWeight={600}>
          {t('dashboard:settings_title')}
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {t('dashboard:settings_description')}
        </Typography>
        
        {/* TODO: Добавить настройки */}
      </Paper>
    </Box>
  )
}
