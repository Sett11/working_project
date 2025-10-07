import { Box, Typography, Paper, Alert, CircularProgress } from '@mui/material'
import { Receipt as ReceiptIcon } from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/store'
import { useSearchParams } from 'react-router-dom'

export default function OrdersPage() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const [searchParams] = useSearchParams()
  
  // Проверяем фильтр из URL
  const filter = searchParams.get('filter')
  const isMyOrders = filter === 'my'
  
  const pageTitle = isMyOrders ? t('dashboard:my_orders') : t('dashboard:all_orders')

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <ReceiptIcon sx={{ fontSize: 40, mr: 2, color: 'primary.main' }} />
        <Typography variant="h4" component="h1" fontWeight={700}>
          {pageTitle}
        </Typography>
      </Box>

      {isMyOrders && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Показаны только ваши заказы
        </Alert>
      )}

      <Paper elevation={2} sx={{ p: 4, borderRadius: 3, minHeight: 400 }}>
        <Box sx={{ 
          display: 'flex', 
          flexDirection: 'column', 
          alignItems: 'center', 
          justifyContent: 'center',
          minHeight: 300
        }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>
            {t('dashboard:no_orders')}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {isMyOrders 
              ? `Фильтр: только заказы пользователя ${user?.username}`
              : 'Показаны все заказы всех пользователей'
            }
          </Typography>
          
          {/* TODO: Добавить список заказов с API */}
        </Box>
      </Paper>
    </Box>
  )
}
