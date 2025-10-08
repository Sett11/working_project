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
  InputAdornment,
  IconButton,
  CircularProgress,
  useTheme,
} from '@mui/material'
import {
  Visibility,
  VisibilityOff,
  LockOutlined,
} from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { loginSchema, type LoginFormData } from '@/types/validation.schemas'
import { useLogin } from '@/hooks/queries'
import LanguageSwitcher from '@/components/common/LanguageSwitcher'

export default function LoginPage() {
  const { t } = useTranslation()
  const theme = useTheme()
  const loginMutation = useLogin()
  
  const [showPassword, setShowPassword] = useState(false)

  // Переиспользуемые стили для TextField (username и password)
  const textFieldSx = {
    '& .MuiOutlinedInput-root': {
      backgroundColor: theme.palette.mode === 'light' ? '#E0F2F1' : theme.palette.grey[800],
      '& fieldset': {
        borderColor: 'primary.main',
        borderWidth: '2px',
      },
      '&:hover fieldset': {
        borderColor: 'primary.dark',
        borderWidth: '2px',
      },
      '&.Mui-focused fieldset': {
        borderColor: 'primary.main',
        borderWidth: '2px',
      },
      '& input': {
        color: 'text.primary',
        fontWeight: 500,
        fontSize: '16px',
      },
      '& input::placeholder': {
        color: 'text.secondary',
        opacity: 0.6,
      },
    },
  }

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

  const onSubmit = (data: LoginFormData) => {
    loginMutation.mutate(data)
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
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
              background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
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
                  disabled={loginMutation.isPending}
                  InputLabelProps={{ 
                    shrink: true,
                    sx: { color: 'text.primary', fontWeight: 600 }
                  }}
                  sx={textFieldSx}
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
                  disabled={loginMutation.isPending}
                  InputLabelProps={{ 
                    shrink: true,
                    sx: { color: 'text.primary', fontWeight: 600 }
                  }}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowPassword(!showPassword)}
                          edge="end"
                          disabled={loginMutation.isPending}
                          sx={{ color: 'primary.main' }}
                        >
                          {showPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                  sx={textFieldSx}
                />
              )}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={loginMutation.isPending}
              sx={{ 
                mt: 3, 
                mb: 2,
                py: 1.5,
                background: `linear-gradient(135deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
                '&:hover': {
                  background: `linear-gradient(135deg, ${theme.palette.primary.dark} 0%, ${theme.palette.primary.main} 100%)`,
                },
              }}
            >
              {loginMutation.isPending ? <CircularProgress size={24} color="inherit" /> : t('auth:login_button')}
            </Button>

            <Box sx={{ textAlign: 'center', mt: 2 }}>
              <Typography variant="body2" color="text.secondary">
                {t('auth:dont_have_account')}{' '}
                <Link
                  component={RouterLink}
                  to="/register"
                  sx={{ color: 'primary.main', fontWeight: 600 }}
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
