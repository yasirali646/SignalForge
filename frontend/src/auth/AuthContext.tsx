import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api } from '../api/client'
import type { UserProfile } from '../types'
import { clearAccessToken, getAccessToken, setAccessToken } from './session'

export type AuthUser = UserProfile

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  authEnabled: boolean
  demoUsername: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

const GUEST_USER: AuthUser = {
  username: 'guest',
  role: 'admin',
  can_manage_competitors: true,
  agent_requests_used: 0,
  agent_requests_limit: null,
  agent_requests_remaining: null,
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)
  const [authEnabled, setAuthEnabled] = useState(true)
  const [demoUsername, setDemoUsername] = useState<string | null>(null)

  const refreshUser = useCallback(async () => {
    const me = await api.getMe()
    setUser(me)
  }, [])

  const bootstrap = useCallback(async () => {
    setLoading(true)
    try {
      const config = await api.getAuthConfig()
      setAuthEnabled(config.auth_enabled)
      setDemoUsername(config.demo_username)
      if (!config.auth_enabled) {
        setUser(GUEST_USER)
        return
      }
      const token = getAccessToken()
      if (!token) {
        setUser(null)
        return
      }
      const me = await api.getMe()
      setUser(me)
    } catch {
      clearAccessToken()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    bootstrap()
  }, [bootstrap])

  useEffect(() => {
    function onUnauthorized() {
      setUser(null)
    }
    window.addEventListener('signalforge:unauthorized', onUnauthorized)
    return () => window.removeEventListener('signalforge:unauthorized', onUnauthorized)
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const result = await api.login(username, password)
    setAccessToken(result.access_token)
    setUser(result.user)
  }, [])

  const logout = useCallback(() => {
    clearAccessToken()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      authEnabled,
      demoUsername,
      login,
      logout,
      refreshUser,
    }),
    [user, loading, authEnabled, demoUsername, login, logout, refreshUser]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
