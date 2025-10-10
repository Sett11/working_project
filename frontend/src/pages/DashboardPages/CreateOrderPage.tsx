import { Box, Typography, Paper, Button, TextField } from '@mui/material'
import { NoteAdd as CreateIcon, ArrowBack as BackIcon } from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

// Zod схема валидации для клиента
const createOrderSchema = z.object({
  // Данные клиента
  clientName: z.string().min(2, 'Имя клиента должно содержать минимум 2 символа'),
  clientPhone: z.string().min(10, 'Номер телефона должен содержать минимум 10 цифр'),
  clientEmail: z.string().email('Некорректный email').optional().or(z.literal('')),
  clientAddress: z.string().optional(),
})

type CreateOrderFormData = z.infer<typeof createOrderSchema>

export default function CreateOrderPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<CreateOrderFormData>({
    resolver: zodResolver(createOrderSchema),
    defaultValues: {
      clientName: '',
      clientPhone: '',
      clientEmail: '',
      clientAddress: '',
    },
  })

  const onSubmit = async (data: CreateOrderFormData) => {
    try {
      console.log('Creating order with data:', data)
      // TODO: Implement order creation logic
      // 1. Create client
      // 2. Select air conditioners (will be implemented in next steps)
      // 3. Select components (will be implemented in next steps)
      // 4. Create compose order
      
      // For now, just log and navigate back
      alert('Создание заказа будет реализовано в следующих шагах')
      navigate('/dashboard/orders')
    } catch (error) {
      console.error('Error creating order:', error)
    }
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <CreateIcon sx={{ fontSize: 40, mr: 2, color: 'primary.main' }} />
          <Typography variant="h4" component="h1" fontWeight={700}>
            {t('dashboard:create_new_order')}
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<BackIcon />}
          onClick={() => navigate('/dashboard/orders')}
        >
          {t('common:back')}
        </Button>
      </Box>

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)}>
        <Paper elevation={2} sx={{ p: 4, borderRadius: 3, mb: 3 }}>
          {/* Информация о клиенте */}
          <Typography variant="h6" gutterBottom fontWeight={600} sx={{ mb: 3 }}>
            {t('dashboard:client_information')}
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Controller
              name="clientName"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label={t('dashboard:client_name')}
                  error={!!errors.clientName}
                  helperText={errors.clientName?.message}
                  required
                  variant="outlined"
                  margin="normal"
                />
              )}
            />

            <Controller
              name="clientPhone"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label={t('dashboard:client_phone')}
                  error={!!errors.clientPhone}
                  helperText={errors.clientPhone?.message}
                  required
                  variant="outlined"
                  margin="normal"
                />
              )}
            />

            <Controller
              name="clientEmail"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  type="email"
                  label={t('dashboard:client_email')}
                  error={!!errors.clientEmail}
                  helperText={errors.clientEmail?.message}
                  variant="outlined"
                  margin="normal"
                />
              )}
            />

            <Controller
              name="clientAddress"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label={t('dashboard:client_address')}
                  error={!!errors.clientAddress}
                  helperText={errors.clientAddress?.message}
                  variant="outlined"
                  margin="normal"
                />
              )}
            />
          </Box>
        </Paper>

        {/* Выбор кондиционеров (заглушка) */}
        <Paper elevation={2} sx={{ p: 4, borderRadius: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight={600} sx={{ mb: 2 }}>
            {t('dashboard:select_air_conditioners')}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t('dashboard:air_conditioner_selection_coming_soon')}
          </Typography>
        </Paper>

        {/* Выбор комплектующих (заглушка) */}
        <Paper elevation={2} sx={{ p: 4, borderRadius: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom fontWeight={600} sx={{ mb: 2 }}>
            {t('dashboard:select_components')}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {t('dashboard:components_selection_coming_soon')}
          </Typography>
        </Paper>

        {/* Actions */}
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
          <Button
            variant="outlined"
            onClick={() => navigate('/dashboard/orders')}
            disabled={isSubmitting}
          >
            {t('common:cancel')}
          </Button>
          <Button
            type="submit"
            variant="contained"
            color="primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? t('common:saving') : t('common:save_draft')}
          </Button>
        </Box>
      </form>
    </Box>
  )
}
