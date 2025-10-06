import { z } from 'zod'

// Схема для логина
export const loginSchema = z.object({
  username: z
    .string()
    .min(3, 'Имя пользователя должно содержать минимум 3 символа')
    .max(50, 'Имя пользователя не должно превышать 50 символов'),
  password: z
    .string()
    .min(6, 'Пароль должен содержать минимум 6 символов')
    .max(100, 'Пароль не должен превышать 100 символов'),
})

export type LoginFormData = z.infer<typeof loginSchema>

// Схема для регистрации
export const registerSchema = z
  .object({
    username: z
      .string()
      .min(3, 'Имя пользователя должно содержать минимум 3 символа')
      .max(50, 'Имя пользователя не должно превышать 50 символов')
      .regex(
        /^[a-zA-Z0-9_]+$/,
        'Имя пользователя может содержать только латинские буквы, цифры и подчеркивание'
      ),
    password: z
      .string()
      .min(6, 'Пароль должен содержать минимум 6 символов')
      .max(100, 'Пароль не должен превышать 100 символов'),
    confirmPassword: z.string(),
    secretKey: z
      .string()
      .min(1, 'Секретный ключ обязателен для регистрации'),
  })
  .refine(data => data.password === data.confirmPassword, {
    message: 'Пароли не совпадают',
    path: ['confirmPassword'],
  })

export type RegisterFormData = z.infer<typeof registerSchema>
