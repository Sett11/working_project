import { Box, Typography, Paper, Alert, CircularProgress, Button } from '@mui/material'
import { Settings as SettingsIcon, People as PeopleIcon } from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/store'
import { Navigate, useNavigate } from 'react-router-dom'

export default function SettingsPage() {
  const { t } = useTranslation()
  const { user, isAuthInitialized } = useAuthStore()
  const navigate = useNavigate()

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
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          {t('dashboard:settings_description')}
        </Typography>
        
        {/* Управление пользователями (только для администраторов) */}
        <Box sx={{ mt: 3, borderTop: '1px solid', borderColor: 'divider', pt: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight={600}>
            {t('dashboard:user_management')}
          </Typography>
          <Button
            variant="outlined"
            color="primary"
            startIcon={<PeopleIcon />}
            onClick={() => navigate('/dashboard/users')}
            sx={{ mt: 2 }}
          >
            {t('dashboard:view_all_users')}
          </Button>
        </Box>
      </Paper>
    </Box>
  )
}
