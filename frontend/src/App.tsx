import React from 'react'
import { Box, Typography, Button, Stack, Paper, AppBar, Toolbar, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Divider, Dialog, DialogTitle, DialogContent, DialogContentText, DialogActions, CircularProgress } from '@mui/material'
import { Logout as LogoutIcon, Settings as SettingsIcon, Receipt as ReceiptIcon, Person as PersonIcon, DeleteForever as DeleteForeverIcon, Home as HomeIcon } from '@mui/icons-material'
import { useTranslation } from 'react-i18next'
import { useNavigate, Outlet, useLocation } from 'react-router-dom'
import { useUIStore, useAuthStore } from './store'
import { useLogout, useDeleteAccount } from './hooks/queries'
import LanguageSwitcher from './components/common/LanguageSwitcher'

const DRAWER_WIDTH = 280

function App() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const { theme, toggleTheme } = useUIStore()
  const { user } = useAuthStore()
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false)
  
  const logoutMutation = useLogout()
  const deleteAccountMutation = useDeleteAccount()

  const handleLogout = () => {
    logoutMutation.mutate()
  }

  const handleDeleteAccount = () => {
    deleteAccountMutation.mutate(undefined, {
      onSuccess: () => {
        setDeleteDialogOpen(false)
        alert(t('dashboard:delete_account_success'))
      },
      onError: () => {
        alert(t('dashboard:delete_account_error'))
        setDeleteDialogOpen(false)
      }
    })
  }

  const menuItems = [
    ...(user?.is_admin ? [{
      text: t('dashboard:system_settings'),
      icon: <SettingsIcon />,
      path: '/dashboard/settings',
      adminOnly: true
    }] : []),
    {
      text: t('dashboard:my_orders'),
      icon: <PersonIcon />,
      path: '/dashboard/orders?filter=my',
      adminOnly: false
    },
    {
      text: t('dashboard:all_orders'),
      icon: <ReceiptIcon />,
      path: '/dashboard/orders',
      adminOnly: false
    }
  ]

  return (
    <Box sx={{ display: 'flex' }}>
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {t('common:app_name')}
          </Typography>
          <Typography variant="body2" sx={{ mr: 2 }}>
            {user?.username}
          </Typography>
          <LanguageSwitcher />
          <Button
            color="inherit"
            startIcon={<HomeIcon />}
            onClick={() => navigate('/')}
            sx={{ ml: 2 }}
          >
            {t('common:home')}
          </Button>
          <Button
            color="inherit"
            startIcon={logoutMutation.isPending ? <CircularProgress size={20} color="inherit" /> : <LogoutIcon />}
            onClick={handleLogout}
            disabled={logoutMutation.isPending}
            sx={{ ml: 2 }}
          >
            {t('auth:logout')}
          </Button>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
          },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto', p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
          <Box>
            <Typography variant="h6" sx={{ px: 2, py: 1, fontWeight: 700, color: 'primary.main' }}>
              {t('dashboard:control_panel')}
            </Typography>
            <Divider sx={{ my: 1 }} />
            <List>
              {menuItems.map((item) => (
                <ListItem key={item.path} disablePadding sx={{ mb: 1 }}>
                  <ListItemButton
                    selected={location.pathname + location.search === item.path}
                    onClick={() => navigate(item.path)}
                    sx={{
                      borderRadius: 2,
                      '&.Mui-selected': {
                        bgcolor: 'primary.main',
                        color: 'white',
                        '&:hover': {
                          bgcolor: 'primary.dark',
                        },
                        '& .MuiListItemIcon-root': {
                          color: 'white',
                        },
                      },
                    }}
                  >
                    <ListItemIcon>
                      {item.icon}
                    </ListItemIcon>
                    <ListItemText primary={item.text} />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          </Box>
          <Box sx={{ mt: 'auto', pb: 2 }}>
            <Divider sx={{ my: 2 }} />
            <Button
              variant="outlined"
              color="error"
              fullWidth
              startIcon={deleteAccountMutation.isPending ? <CircularProgress size={20} color="error" /> : <DeleteForeverIcon />}
              onClick={() => setDeleteDialogOpen(true)}
              disabled={deleteAccountMutation.isPending}
              sx={{ borderRadius: 2 }}
            >
              {t('dashboard:delete_account')}
            </Button>
          </Box>
        </Box>
      </Drawer>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          minHeight: '100vh',
          mt: 8,
        }}
      >
        <Outlet />
      </Box>

      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>{t('dashboard:delete_account_confirm_title')}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t('dashboard:delete_account_confirm_text')}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setDeleteDialogOpen(false)}
            disabled={deleteAccountMutation.isPending}
          >
            {t('common:cancel')}
          </Button>
          <Button 
            onClick={handleDeleteAccount} 
            color="error" 
            variant="contained"
            disabled={deleteAccountMutation.isPending}
            startIcon={deleteAccountMutation.isPending ? <CircularProgress size={20} color="inherit" /> : undefined}
          >
            {deleteAccountMutation.isPending ? t('common:deleting') : t('common:delete')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default App
