import { Box, Typography, Paper, Alert, Button } from '@mui/material'
import { Receipt as ReceiptIcon, Add as AddIcon } from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/store'
import { useSearchParams, useNavigate } from 'react-router-dom'

export default function OrdersPage() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  
  // Проверяем фильтр из URL
  const filter = searchParams.get('filter')
  const isMyOrders = filter === 'my'
  
  const pageTitle = isMyOrders ? t('dashboard:my_orders') : t('dashboard:all_orders')

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <ReceiptIcon sx={{ fontSize: 40, mr: 2, color: 'primary.main' }} />
          <Typography variant="h4" component="h1" fontWeight={700}>
            {pageTitle}
          </Typography>
        </Box>
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={() => navigate('/dashboard/orders/create')}
          sx={{ px: 3 }}
        >
          {t('dashboard:create_new_order')}
        </Button>
      </Box>

      {isMyOrders && (
        <Alert severity="info" sx={{ mb: 3 }}>
          {t('dashboard:showing_only_your_orders')}
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
              ? t('dashboard:filter_user_orders', { username: user?.username })
              : t('dashboard:showing_all_users_orders')
            }
          </Typography>
          
          {/* TODO: Добавить список заказов с API */}
        </Box>
      </Paper>
    </Box>
  )
}
