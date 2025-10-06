import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AirConditioner, Component } from '@/types'

interface CartItem {
  type: 'airconditioner' | 'component'
  item: AirConditioner | Component
  quantity: number
}

interface CartState {
  items: CartItem[]

  addItem: (item: CartItem) => void
  removeItem: (id: number, type: 'airconditioner' | 'component') => void
  updateQuantity: (
    id: number,
    type: 'airconditioner' | 'component',
    quantity: number
  ) => void
  clearCart: () => void
  getTotalPrice: () => number
  getItemCount: () => number
}

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      items: [],

      addItem: newItem => {
        set(state => {
          const existingIndex = state.items.findIndex(
            i => i.item.id === newItem.item.id && i.type === newItem.type
          )

          if (existingIndex !== -1) {
            const newItems = [...state.items]
            newItems[existingIndex].quantity += newItem.quantity
            return { items: newItems }
          }

          return { items: [...state.items, newItem] }
        })
      },

      removeItem: (id, type) => {
        set(state => ({
          items: state.items.filter(i => !(i.item.id === id && i.type === type)),
        }))
      },

      updateQuantity: (id, type, quantity) => {
        if (quantity <= 0) {
          get().removeItem(id, type)
          return
        }
        set(state => ({
          items: state.items.map(i =>
            i.item.id === id && i.type === type ? { ...i, quantity } : i
          ),
        }))
      },

      clearCart: () => set({ items: [] }),

      getTotalPrice: () => {
        const items = get().items
        return items.reduce((total, item) => {
          const price =
            'retail_price_byn' in item.item
              ? item.item.retail_price_byn
              : item.item.price
          return total + Number(price) * item.quantity
        }, 0)
      },

      getItemCount: () => {
        const items = get().items
        return items.reduce((count, item) => count + item.quantity, 0)
      },
    }),
    {
      name: 'cart-storage',
    }
  )
)