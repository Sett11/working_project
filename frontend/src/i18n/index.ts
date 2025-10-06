import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'ru',
    lng: 'ru',
    debug: false,

    interpolation: {
      escapeValue: false,
    },

    resources: {
      ru: {
        common: {
          app_name: 'Система продаж кондиционеров',
          welcome: 'Добро пожаловать',
          loading: 'Загрузка...',
          error: 'Ошибка',
          success: 'Успешно',
          save: 'Сохранить',
          cancel: 'Отмена',
          delete: 'Удалить',
          edit: 'Редактировать',
          close: 'Закрыть',
          search: 'Поиск',
          filter: 'Фильтр',
          back: 'Назад',
          next: 'Далее',
          submit: 'Отправить',
        },
      auth: {
        login: 'Вход',
        register: 'Регистрация',
        logout: 'Выход',
        username: 'Имя пользователя',
        password: 'Пароль',
        login_button: 'Войти',
        register_button: 'Зарегистрироваться',
        already_have_account: 'Уже есть аккаунт?',
        dont_have_account: 'Нет аккаунта?',
      },
        products: {
          air_conditioners: 'Кондиционеры',
          components: 'Комплектующие',
          brand: 'Бренд',
          model: 'Модель',
          power: 'Мощность',
          price: 'Цена',
          add_to_cart: 'Добавить в корзину',
        },
      },
      en: {
        common: {
          app_name: 'AirCon Sales System',
          welcome: 'Welcome',
          loading: 'Loading...',
          error: 'Error',
          success: 'Success',
          save: 'Save',
          cancel: 'Cancel',
          delete: 'Delete',
          edit: 'Edit',
          close: 'Close',
          search: 'Search',
          filter: 'Filter',
          back: 'Back',
          next: 'Next',
          submit: 'Submit',
        },
      auth: {
        login: 'Login',
        register: 'Register',
        logout: 'Logout',
        username: 'Username',
        password: 'Password',
        login_button: 'Log In',
        register_button: 'Register',
        already_have_account: 'Already have an account?',
        dont_have_account: "Don't have an account?",
      },
        products: {
          air_conditioners: 'Air Conditioners',
          components: 'Components',
          brand: 'Brand',
          model: 'Model',
          power: 'Power',
          price: 'Price',
          add_to_cart: 'Add to Cart',
        },
      },
    },
  })

export default i18n