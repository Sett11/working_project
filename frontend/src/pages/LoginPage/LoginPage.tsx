import { useState } from 'react'
import { useNavigate, Link as RouterLink } from 'react-router-dom'
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
  LockOutlined,
} from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { loginSchema, type LoginFormData } from '@/types/validation.schemas'
import { authService } from '@/api/services/auth.service'
import { useAuthStore } from '@/store'
import LanguageSwitcher from '@/components/common/LanguageSwitcher'

export default function LoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      username: '',
      password: '',
    },
  })

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await authService.login(data)
      setAuth(response.user, response.token)
      navigate('/', { replace: true })
    } catch (err: any) {
      console.error('Login error:', err)
      setError(
        err.response?.data?.detail || t('auth:login_error')
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #00897B 0%, #00695C 100%)',
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
              background: 'linear-gradient(135deg, #00897B 0%, #00695C 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mb: 1.5,
            }}
          >
            <LockOutlined sx={{ fontSize: 24, color: 'white' }} />
          </Box>

          <Typography component="h1" variant="h4" fontWeight="700" gutterBottom sx={{ mb: 1 }}>
            {t('auth:login')}
          </Typography>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t('common:app_name')}
          </Typography>

          {error && (
            <Alert severity="error" sx={{ width: '100%', mb: 2 }}>
              {error}
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
                  disabled={isLoading}
                  InputLabelProps={{ 
                    shrink: true,
                    sx: { color: '#333', fontWeight: 600 }
                  }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: '#E0F2F1',
                      '& fieldset': {
                        borderColor: '#00897B',
                        borderWidth: '2px',
                      },
                      '&:hover fieldset': {
                        borderColor: '#00695C',
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
                  }}
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
                  autoComplete="current-password"
                  error={!!errors.password}
                  helperText={errors.password?.message}
                  disabled={isLoading}
                  InputLabelProps={{ 
                    shrink: true,
                    sx: { color: '#333', fontWeight: 600 }
                  }}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowPassword(!showPassword)}
                          edge="end"
                          disabled={isLoading}
                          sx={{ color: '#00897B' }}
                        >
                          {showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      backgroundColor: '#E0F2F1',
                      '& fieldset': {
                        borderColor: '#00897B',
                        borderWidth: '2px',
                      },
                      '&:hover fieldset': {
                        borderColor: '#00695C',
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
                  }}
                />
              )}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={isLoading}
              sx={{ 
                mt: 3, 
                mb: 2,
                py: 1.5,
                background: 'linear-gradient(135deg, #00897B 0%, #00695C 100%)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #00695C 0%, #00897B 100%)',
                },
              }}
            >
              {isLoading ? <CircularProgress size={24} color="inherit" /> : t('auth:login_button')}
            </Button>

            <Box sx={{ textAlign: 'center', mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                {t('auth:dont_have_account')}{' '}
                <Link
                  component={RouterLink}
                  to="/register"
                  sx={{ color: '#00897B', fontWeight: 600 }}
                >
                  {t('auth:register')}
                </Link>
              </Typography>
            </Box>
          </Box>
        </Paper>
      </Container>
    </Box>
  )
}
