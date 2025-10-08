import { useState } from 'react'
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Card,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  useMediaQuery,
  useTheme,
} from '@mui/material'
import {
  Menu as MenuIcon,
  ExpandMore as ExpandMoreIcon,
  AcUnit as AcUnitIcon,
  Speed as SpeedIcon,
  Security as SecurityIcon,
  Support as SupportIcon,
} from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from '@/components/common/LanguageSwitcher'
import LandingSidebar from '@/components/layout/LandingSidebar'
import heroImage from '@/images/photo_2025-10-07_16-32-35.jpg'

export default function LandingPage() {
  const { t } = useTranslation()
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  // Начальное состояние: на десктопе сайдбар открыт, на мобильных - закрыт
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile)

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  const features = [
    {
      icon: <AcUnitIcon sx={{ fontSize: { xs: 56, sm: 64 }, color: 'primary.main' }} />,
      title: t('landing:feature_1_title'),
      description: t('landing:feature_1_desc'),
    },
    {
      icon: <SpeedIcon sx={{ fontSize: { xs: 56, sm: 64 }, color: 'primary.main' }} />,
      title: t('landing:feature_2_title'),
      description: t('landing:feature_2_desc'),
    },
    {
      icon: <SecurityIcon sx={{ fontSize: { xs: 56, sm: 64 }, color: 'primary.main' }} />,
      title: t('landing:feature_3_title'),
      description: t('landing:feature_3_desc'),
    },
    {
      icon: <SupportIcon sx={{ fontSize: { xs: 56, sm: 64 }, color: 'primary.main' }} />,
      title: t('landing:feature_4_title'),
      description: t('landing:feature_4_desc'),
    },
  ]

  const faqs = [
    {
      question: t('landing:faq_q1'),
      answer: t('landing:faq_a1'),
    },
    {
      question: t('landing:faq_q2'),
      answer: t('landing:faq_a2'),
    },
    {
      question: t('landing:faq_q3'),
      answer: t('landing:faq_a3'),
    },
    {
      question: t('landing:faq_q4'),
      answer: t('landing:faq_a4'),
    },
  ]

  return (
    <Box sx={{ 
      minHeight: '100vh', 
      width: '100%',
      margin: 0,
      padding: 0,
      bgcolor: 'background.default'
    }}>
      {/* AppBar */}
      <AppBar position="sticky" elevation={2} sx={{ zIndex: 1100 }}>
        <Toolbar sx={{ 
          px: { xs: 2, sm: 3, md: 4, lg: 6 },
          py: { xs: 0.5, sm: 1 },
          minHeight: { xs: 56, sm: 64, md: 70 }
        }}>
          <Typography 
            variant="h6" 
            component="div" 
            sx={{ 
              flexGrow: 1, 
              fontWeight: 800,
              fontSize: { xs: '1.25rem', sm: '1.5rem', md: '1.75rem' },
              letterSpacing: '0.5px'
            }}
          >
            Everis
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 1, sm: 1.5, md: 2 } }}>
            <LanguageSwitcher />
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="end"
              onClick={toggleSidebar}
              sx={{ 
                ml: { xs: 0.5, sm: 1 },
                p: { xs: 1, sm: 1.25, md: 1.5 },
                transition: 'transform 0.2s',
                '&:hover': {
                  transform: 'scale(1.1)'
                }
              }}
            >
              <MenuIcon sx={{ fontSize: { xs: 26, sm: 28, md: 30 } }} />
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Sidebar */}
      <LandingSidebar
        open={sidebarOpen}
        onClose={toggleSidebar}
        variant={isMobile ? 'temporary' : 'persistent'}
      />

      {/* Hero Section */}
      <Box
        sx={{
          background: 'linear-gradient(135deg, #00897B 0%, #00695C 100%)',
          color: 'white',
          py: { xs: 8, sm: 10, md: 12, lg: 16 },
          textAlign: 'center',
          width: '100%',
          px: { xs: 3, sm: 4, md: 6, lg: 8, xl: 10 },
          position: 'relative',
          overflow: 'hidden',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'radial-gradient(circle at 20% 50%, rgba(255,255,255,0.1) 0%, transparent 50%)',
            pointerEvents: 'none'
          }
        }}
      >
        <Box sx={{ position: 'relative', zIndex: 1 }}>
          <Box
            component="img"
            src={heroImage}
            alt="Everis"
            sx={{
              width: { xs: '70%', sm: '50%', md: 380, lg: 420 },
              maxWidth: 480,
              height: 'auto',
              mb: { xs: 4, sm: 5, md: 6 },
              borderRadius: { xs: 3, sm: 4 },
              boxShadow: '0 12px 48px rgba(0,0,0,0.4)',
              transition: 'transform 0.3s ease',
              '&:hover': {
                transform: 'scale(1.02)'
              }
            }}
          />
          <Typography
            variant="h2" 
            component="h1" 
            fontWeight={800} 
            gutterBottom
            sx={{
              fontSize: { xs: '2.25rem', sm: '3rem', md: '3.75rem', lg: '4.5rem' },
              lineHeight: 1.2,
              mb: { xs: 2, sm: 3 },
              textShadow: '0 2px 20px rgba(0,0,0,0.2)'
            }}
          >
            {t('landing:hero_title')}
          </Typography>
          <Typography 
            variant="h5" 
            sx={{ 
              opacity: 0.95, 
              maxWidth: { xs: '100%', sm: 700, md: 850 },
              mx: 'auto',
              fontSize: { xs: '1.125rem', sm: '1.375rem', md: '1.625rem' },
              lineHeight: 1.6,
              fontWeight: 400,
              px: { xs: 2, sm: 3 }
            }}
          >
            {t('landing:hero_subtitle')}
          </Typography>
        </Box>
      </Box>

      {/* About Section */}
      <Box sx={{ 
        py: { xs: 8, sm: 10, md: 12, lg: 14 }, 
        px: { xs: 3, sm: 4, md: 6, lg: 8, xl: 10 }, 
        width: '100%',
        bgcolor: 'background.paper'
      }}>
        <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
          <Typography
            variant="h3" 
            component="h2" 
            textAlign="center" 
            fontWeight={700} 
            gutterBottom
            sx={{
              fontSize: { xs: '2rem', sm: '2.75rem', md: '3.5rem', lg: '4rem' },
              mb: { xs: 2, sm: 3 },
              color: 'primary.main',
              lineHeight: 1.2
            }}
          >
            {t('landing:about_title')}
          </Typography>
          <Typography
            variant="h6"
            textAlign="center"
            color="text.secondary"
            sx={{ 
              mb: { xs: 6, sm: 8, md: 10 }, 
              fontSize: { xs: '1.125rem', sm: '1.25rem', md: '1.375rem' },
              lineHeight: 1.7,
              maxWidth: 900,
              mx: 'auto',
              px: { xs: 2, sm: 3 }
            }}
          >
            {t('landing:about_description')}
          </Typography>

          {/* Features Grid */}
          <Grid 
            container 
            spacing={{ xs: 3, sm: 3, md: 4 }}
            sx={{ 
              maxWidth: 1300, 
              mx: 'auto',
              justifyContent: 'center'
            }}
          >
            {features.map((feature, index) => (
              <Grid 
                size={{ xs: 12, sm: 6, md: 6, lg: 3 }}
                key={index}
                sx={{
                  display: 'flex',
                  justifyContent: 'center'
                }}
              >
                <Card
                  elevation={2}
                  sx={{
                    width: '100%',
                    maxWidth: { xs: '100%', sm: 360, md: 320 },
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'flex-start',
                    p: { xs: 3, sm: 3.5, md: 4 },
                    borderRadius: 3,
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    border: '1px solid',
                    borderColor: 'divider',
                    bgcolor: 'background.paper',
                    '&:hover': {
                      transform: 'translateY(-12px)',
                      boxShadow: '0 16px 48px rgba(0, 137, 123, 0.15)',
                      borderColor: 'primary.main',
                      bgcolor: 'background.paper',
                    },
                  }}
                >
                  <Box sx={{ 
                    mb: { xs: 2.5, sm: 3 },
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: { xs: 72, sm: 80 },
                    height: { xs: 72, sm: 80 },
                    transition: 'transform 0.3s ease',
                    '&:hover': {
                      transform: 'scale(1.15) rotate(5deg)'
                    }
                  }}>
                    {feature.icon}
                  </Box>
                  <Typography 
                    variant="h6" 
                    fontWeight={600} 
                    textAlign="center"
                    sx={{
                      fontSize: { xs: '1.125rem', sm: '1.25rem' },
                      mb: { xs: 1.5, sm: 2 },
                      lineHeight: 1.3,
                      minHeight: { xs: 'auto', sm: '2.5em' },
                      display: 'flex',
                      alignItems: 'center'
                    }}
                  >
                    {feature.title}
                  </Typography>
                  <Typography 
                    variant="body2" 
                    color="text.secondary" 
                    textAlign="center"
                    sx={{
                      fontSize: { xs: '0.9375rem', sm: '1rem' },
                      lineHeight: 1.7,
                      flexGrow: 1
                    }}
                  >
                    {feature.description}
                  </Typography>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      </Box>

      {/* FAQ Section */}
      <Box sx={{ 
        bgcolor: '#fafbfc', 
        py: { xs: 8, sm: 10, md: 12, lg: 14 }, 
        width: '100%', 
        px: { xs: 3, sm: 4, md: 6, lg: 8, xl: 10 },
        borderTop: '1px solid',
        borderColor: 'divider'
      }}>
        <Box sx={{ maxWidth: 1100, mx: 'auto' }}>
          <Typography
            variant="h3" 
            component="h2" 
            textAlign="center" 
            fontWeight={700} 
            gutterBottom
            sx={{
              fontSize: { xs: '2rem', sm: '2.75rem', md: '3.5rem', lg: '4rem' },
              color: 'primary.main',
              mb: { xs: 2, sm: 3 },
              lineHeight: 1.2
            }}
          >
            {t('landing:faq_title')}
          </Typography>
          <Typography
            variant="body1"
            textAlign="center"
            sx={{ 
              mb: { xs: 5, sm: 7, md: 8 }, 
              color: 'text.secondary',
              fontSize: { xs: '1.0625rem', sm: '1.125rem', md: '1.1875rem' },
              lineHeight: 1.7,
              maxWidth: 700,
              mx: 'auto'
            }}
          >
            {t('landing:faq_subtitle')}
          </Typography>

          <Box sx={{ maxWidth: 900, mx: 'auto' }}>
            {faqs.map((faq, index) => (
              <Accordion 
                key={index} 
                disableGutters
                elevation={0}
                sx={{ 
                  mb: { xs: 2, sm: 2.5 },
                  '&:before': { display: 'none' },
                  bgcolor: 'background.paper',
                  borderRadius: 2,
                  border: '1px solid',
                  borderColor: 'divider',
                  transition: 'all 0.2s ease',
                  '&:hover': {
                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                    borderColor: 'primary.light'
                  },
                  '&.Mui-expanded': {
                    boxShadow: '0 6px 16px rgba(0,0,0,0.1)',
                    borderColor: 'primary.main'
                  }
                }}
              >
                <AccordionSummary 
                  expandIcon={<ExpandMoreIcon sx={{ color: 'primary.main' }} />}
                  sx={{
                    px: { xs: 2.5, sm: 3, md: 4 },
                    py: { xs: 1.5, sm: 2 },
                    '& .MuiAccordionSummary-content': {
                      my: { xs: 1, sm: 1.5 }
                    },
                    '&:hover': {
                      bgcolor: 'action.hover'
                    }
                  }}
                >
                  <Typography 
                    fontWeight={600} 
                    color="text.primary"
                    sx={{
                      fontSize: { xs: '1rem', sm: '1.0625rem', md: '1.125rem' },
                      lineHeight: 1.5,
                      fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                      letterSpacing: '-0.005em'
                    }}
                  >
                    {faq.question}
                  </Typography>
                </AccordionSummary>
                <AccordionDetails sx={{ 
                  px: { xs: 2.5, sm: 3, md: 4 },
                  py: { xs: 2, sm: 2.5, md: 3 },
                  pt: 0,
                  bgcolor: '#f8f9fa'
                }}>
                  <Typography 
                    sx={{
                      fontSize: { xs: '0.9375rem', sm: '1rem', md: '1.0625rem' },
                      lineHeight: 1.8,
                      color: '#34495e',
                      fontWeight: 400,
                      letterSpacing: '0.01em',
                      fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                      textAlign: 'justify',
                      hyphens: 'auto'
                    }}
                  >
                    {faq.answer}
                  </Typography>
                </AccordionDetails>
              </Accordion>
            ))}
          </Box>
        </Box>
      </Box>

      {/* Footer */}
      <Box sx={{ 
        background: 'linear-gradient(135deg, #00897B 0%, #00695C 100%)', 
        color: 'white', 
        py: { xs: 5, sm: 6, md: 7 }, 
        textAlign: 'center', 
        width: '100%', 
        px: { xs: 3, sm: 4, md: 6 },
        borderTop: '3px solid',
        borderColor: 'primary.light'
      }}>
        <Box sx={{ maxWidth: 800, mx: 'auto' }}>
          <Typography 
            variant="body1" 
            gutterBottom 
            sx={{ 
              fontSize: { xs: '1rem', sm: '1.0625rem', md: '1.125rem' },
              fontWeight: 500,
              mb: 1.5
            }}
          >
            © {new Date().getFullYear()} Everis - {t('landing:footer_text')}
          </Typography>
          <Typography 
            variant="body2" 
            sx={{ 
              opacity: 0.9, 
              fontSize: { xs: '0.9375rem', sm: '1rem' },
              lineHeight: 1.6
            }}
          >
            {t('landing:footer_tagline')}
          </Typography>
        </Box>
      </Box>
    </Box>
  )
}
