import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  IconButton,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Tooltip,
} from '@mui/material'
import { Language as LanguageIcon } from '@mui/icons-material'
import Flag from 'react-world-flags'

const languages = [
  { code: 'ru', name: 'Русский', flagCode: 'RU' },
  { code: 'en', name: 'English', flagCode: 'GB' },
]

export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const open = Boolean(anchorEl)

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget)
  }

  const handleClose = () => {
    setAnchorEl(null)
  }

  const handleLanguageChange = (languageCode: string) => {
    i18n.changeLanguage(languageCode)
    handleClose()
  }

  return (
    <>
      <Tooltip title={t('common.changeLanguage')}>
        <IconButton
          onClick={handleClick}
          size="large"
          aria-label="change language"
          aria-controls={open ? 'language-menu' : undefined}
          aria-haspopup="true"
          aria-expanded={open ? 'true' : undefined}
          sx={{
            color: 'white',
            bgcolor: 'rgba(255, 255, 255, 0.2)',
            '&:hover': {
              bgcolor: 'rgba(255, 255, 255, 0.3)',
            },
          }}
        >
          <LanguageIcon />
        </IconButton>
      </Tooltip>
      <Menu
        id="language-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          'aria-labelledby': 'language-button',
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        {languages.map((language) => (
          <MenuItem
            key={language.code}
            onClick={() => handleLanguageChange(language.code)}
            selected={language.code === i18n.language}
            aria-label={language.name}
          >
            <ListItemIcon aria-hidden="true" sx={{ minWidth: 32 }}>
              <Flag
                code={language.flagCode}
                style={{ width: '24px', height: '18px', objectFit: 'cover' }}
              />
            </ListItemIcon>
            <ListItemText>
              {language.name}
            </ListItemText>
          </MenuItem>
        ))}
      </Menu>
    </>
  )
}
