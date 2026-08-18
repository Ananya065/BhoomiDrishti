import React, { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = sessionStorage.getItem('bd_user')
    return raw ? JSON.parse(raw) : null
  })

  const login = (userData) => {
    setUser(userData)
    sessionStorage.setItem('bd_user', JSON.stringify(userData))
  }
  const logout = () => {
    setUser(null)
    sessionStorage.removeItem('bd_user')
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
