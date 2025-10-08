import { useState } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  Box,
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Link,
  Alert,
  InputAdornment,
  IconButton,
  CircularProgress,
} from '@mui/material'
import {
  Visibility,
  VisibilityOff,
  PersonAddOutlined,
} from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { registerSchema, type RegisterFormData } from '@/types/validation.schemas'
import { useRegister } from '@/hooks/queries'
import LanguageSwitcher from '@/components/common/LanguageSwitcher'

export default function RegisterPage() {
  const { t } = useTranslation()
  const registerMutation = useRegister()
  
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  // Общие стили для всех TextField
  const textFieldSxProps = {
    '& .MuiOutlinedInput-root': {
      backgroundColor: '#E0F2F1',
      '& fieldset': {
        borderColor: '#00897B',
        borderWidth: '2px',
      },
      '&:hover fieldset': {
        borderColor: '#4DB6AC',
        borderWidth: '2px',
      },
      '&.Mui-focused fieldset': {
        borderColor: '#00897B',
        borderWidth: '2px',
      },
      '& input': {
        color: '#000',
        fontWeight: 500,
        fontSize: '16px',
      },
      '& input::placeholder': {
        color: '#000',
        opacity: 0.6,
      },
    },
  }

  const textFieldLabelProps = {
    shrink: true,
    sx: { color: '#333', fontWeight: 600 },
  }

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: '',
      password: '',
      confirmPassword: '',
      secretKey: '',
    },
  })

  const onSubmit = (data: RegisterFormData) => {
    const { confirmPassword, secretKey, ...rest } = data
    const registerData = {
      ...rest,
      secret_key: secretKey
    }
    registerMutation.mutate(registerData)
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #00897B 0%, #4DB6AC 100%)',
        py: 4,
        position: 'relative',
      }}
    >
      <Box sx={{ position: 'absolute', top: 16, left: 16, zIndex: 10 }}>
        <LanguageSwitcher />
      </Box>
      <Container maxWidth="sm" sx={{ mt: 10 }}>
        <Paper
          elevation={12}
          sx={{
            p: 4,
            pt: 2,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            borderRadius: 3,
            background: '#ffffff',
          }}
        >
          <Box
            sx={{
              width: 48,
              height: 48,
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #00897B 0%, #4DB6AC 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mb: 1.5,
            }}
          >
            <PersonAddOutlined sx={{ fontSize: 24, color: 'white' }} />
          </Box>

          <Typography component="h1" variant="h4" fontWeight="700" gutterBottom sx={{ mb: 1 }}>
            {t('auth:register')}
          </Typography>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('common:app_name')}
          </Typography>

          {registerMutation.isError && (
            <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
              {(registerMutation.error as any)?.response?.data?.detail || t('auth:registration_error')}
            </Alert>
          )}

          {registerMutation.isSuccess && (
            <Alert severity="success" sx={{ width: '100%', mb: 2 }}>
              {t('auth:registration_success')}
            </Alert>
          )}

          <Box
            component="form"
            onSubmit={handleSubmit(onSubmit)}
            sx={{ width: '100%', mt: 2 }}
          >
            <Controller
              name="username"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label={t('auth:username')}
                  placeholder={t('auth:username_placeholder')}
                  variant="outlined"
                  fullWidth
                  margin="normal"
                  autoComplete="username"
                  autoFocus
                  error={!!errors.username}
                  helperText={errors.username?.message}
                  disabled={registerMutation.isPending || registerMutation.isSuccess}
                  InputLabelProps={textFieldLabelProps}
                  sx={textFieldSxProps}
                />
              )}
            />

            <Controller
              name="password"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label={t('auth:password')}
                  placeholder={t('auth:password_placeholder')}
                  type={showPassword ? 'text' : 'password'}
                  variant="outlined"
                  fullWidth
                  margin="normal"
                  autoComplete="new-password"
                  error={!!errors.password}
                  helperText={errors.password?.message}
                  disabled={registerMutation.isPending || registerMutation.isSuccess}
                  InputLabelProps={textFieldLabelProps}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowPassword(!showPassword)}
                          edge="end"
                          disabled={registerMutation.isPending || registerMutation.isSuccess}
                          sx={{ color: '#00897B' }}
                        >
                          {showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={textFieldSxProps}
                />
              )}
            />

            <Controller
              name="confirmPassword"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label={t('auth:confirm_password')}
                  placeholder={t('auth:confirm_password_placeholder')}
                  type={showConfirmPassword ? 'text' : 'password'}
                  variant="outlined"
                  fullWidth
                  margin="normal"
                  autoComplete="new-password"
                  error={!!errors.confirmPassword}
                  helperText={errors.confirmPassword?.message}
                  disabled={registerMutation.isPending || registerMutation.isSuccess}
                  InputLabelProps={textFieldLabelProps}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          edge="end"
                          disabled={registerMutation.isPending || registerMutation.isSuccess}
                          sx={{ color: '#00897B' }}
                        >
                          {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={textFieldSxProps}
                />
              )}
            />

            <Controller
              name="secretKey"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  label={t('auth:secret_key')}
                  placeholder={t('auth:secret_key_placeholder')}
                  variant="outlined"
                  fullWidth
                  margin="normal"
                  error={!!errors.secretKey}
                  helperText={errors.secretKey?.message || t('auth:secret_key_helper')}
                  disabled={registerMutation.isPending || registerMutation.isSuccess}
                  InputLabelProps={textFieldLabelProps}
                  sx={textFieldSxProps}
                />
              )}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={registerMutation.isPending || registerMutation.isSuccess}
              sx={{ 
                mt: 3, 
                mb: 2,
                py: 1.5,
                background: 'linear-gradient(135deg, #00897B 0%, #4DB6AC 100%)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #4DB6AC 0%, #00897B 100%)',
                },
              }}
            >
              {registerMutation.isPending ? (
                <CircularProgress size={24} color="inherit" />
              ) : registerMutation.isSuccess ? (
                t('auth:registration_success_short')
              ) : (
                t('auth:register_button')
              )}
            </Button>

            <Box sx={{ textAlign: 'center', mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                {t('auth:already_have_account')}{' '}
                <Link
                  component={RouterLink}
                  to="/login"
                  sx={{ color: '#00897B', fontWeight: 600 }}
                >
                  {t('auth:login')}
                </Link>
              </Typography>
            </Box>
          </Box>
        </Paper>
      </Container>
    </Box>
  )
}
