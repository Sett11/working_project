import { Box, Typography, Paper, CircularProgress, Alert, Chip, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from '@mui/material'
import { People as PeopleIcon, CheckCircle as ActiveIcon, Cancel as InactiveIcon, AdminPanelSettings as AdminIcon } from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/store'
import { Navigate } from 'react-router-dom'
import { useUsers } from '@/hooks/queries/useUsers'
import type { UserResponse } from '@/types'
import dayjs from 'dayjs'

export default function UsersPage() {
  const { t } = useTranslation()
  const { user, isAuthInitialized } = useAuthStore()
  const { data: users, isLoading } = useUsers()

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
        <PeopleIcon sx={{ fontSize: 40, mr: 2, color: 'primary.main' }} />
        <Typography variant="h4" component="h1" fontWeight={700}>
          {t('dashboard:all_users')}
        </Typography>
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        {t('dashboard:users_admin_only')}
      </Alert>

      <Paper elevation={2} sx={{ p: 4, borderRadius: 3 }}>
        {isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
            <CircularProgress />
          </Box>
        )}

        {!isLoading && users && Array.isArray(users) && users.length === 0 && (
          <Box sx={{ textAlign: 'center', py: 6 }}>
            <Typography variant="h6" color="text.secondary">
              {t('dashboard:no_users')}
            </Typography>
          </Box>
        )}

        {!isLoading && users && Array.isArray(users) && users.length > 0 && (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell><strong>ID</strong></TableCell>
                  <TableCell><strong>{t('dashboard:username')}</strong></TableCell>
                  <TableCell><strong>{t('dashboard:email')}</strong></TableCell>
                  <TableCell align="center"><strong>{t('dashboard:status')}</strong></TableCell>
                  <TableCell align="center"><strong>{t('dashboard:role')}</strong></TableCell>
                  <TableCell><strong>{t('dashboard:created_at')}</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map((user: UserResponse) => (
                  <TableRow key={user.id} hover>
                    <TableCell>{user.id}</TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={500}>
                        {user.username}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {user.email || '—'}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      {user.is_active ? (
                        <Chip
                          icon={<ActiveIcon />}
                          label={t('dashboard:active')}
                          color="success"
                          size="small"
                        />
                      ) : (
                        <Chip
                          icon={<InactiveIcon />}
                          label={t('dashboard:inactive')}
                          color="default"
                          size="small"
                        />
                      )}
                    </TableCell>
                    <TableCell align="center">
                      {user.is_admin ? (
                        <Chip
                          icon={<AdminIcon />}
                          label={t('dashboard:admin')}
                          color="primary"
                          size="small"
                        />
                      ) : (
                        <Chip
                          label={t('dashboard:user')}
                          color="default"
                          variant="outlined"
                          size="small"
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {dayjs(user.created_at).format('DD.MM.YYYY HH:mm')}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  )
}
