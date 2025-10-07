import { Box, Container, Typography, Button, Paper } from '@mui/material'
import { Home as HomeIcon, Login as LoginIcon } from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store'

export default function NotFoundPage() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()

  const handleNavigation = () => {
    if (isAuthenticated) {
      navigate('/')
    } else {
      navigate('/login')
    }
  }

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            p: 4,
            textAlign: 'center',
            width: '100%',
          }}
        >
          {/* Большая цифра 404 */}
          <Typography
            variant="h1"
            component="h1"
            sx={{
              fontSize: { xs: '6rem', sm: '8rem' },
              fontWeight: 700,
              color: 'primary.main',
              mb: 2,
            }}
          >
            404
          </Typography>

          {/* Заголовок ошибки */}
          <Typography
            variant="h5"
            component="h2"
            gutterBottom
            sx={{ mb: 2, fontWeight: 600 }}
          >
            Страница не найдена
          </Typography>

          {/* Описание */}
          <Typography
            variant="body1"
            color="text.secondary"
            sx={{ mb: 4 }}
          >
            К сожалению, запрашиваемая вами страница не существует или была перемещена.
          </Typography>

          {/* Кнопка навигации */}
          <Button
            variant="contained"
            size="large"
            startIcon={isAuthenticated ? <HomeIcon /> : <LoginIcon />}
            onClick={handleNavigation}
            sx={{ minWidth: 200 }}
          >
            {isAuthenticated ? 'На главную' : 'Войти в систему'}
          </Button>
        </Paper>
      </Box>
    </Container>
  )
}

