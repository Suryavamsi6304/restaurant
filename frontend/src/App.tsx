import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { BrowserRouter, Link, Route, Routes, useNavigate, useSearchParams } from 'react-router-dom'
import './App.css'
import { apiRequest } from './api'

type StaffRole = 'ADMIN' | 'CHEF' | 'WAITRESS'
type Role = StaffRole | 'CUSTOMER'

type Tokens = {
  access_token: string
  refresh_token: string
  role: Role
}

type User = {
  id: number
  username: string
  role: StaffRole
  status: string
  created_at: string
}

type Table = {
  id: number
  table_number: string
  qr_code_value: string
  status: string
}

type MenuCategory = {
  id: number
  name: string
  is_active: boolean
}

type MenuItem = {
  id: number
  name: string
  description: string
  price: number
  category_id: number | null
  category_name: string | null
  food_type: 'VEG' | 'NON_VEG'
  is_available: boolean
  stock_qty: number | null
  image_url: string | null
  updated_at: string
}

type TableSession = {
  id: number
  table_id: number
  table_number: string
  customer_id: number
  customer_mobile_number: string
  started_at: string
  ended_at: string | null
  status: string
}

type AuditLog = {
  id: number
  actor_type: string
  actor_id: number | null
  action: string
  entity_type: string
  entity_id: number | null
  details: Record<string, unknown>
  created_at: string
}

const storageKey = 'restaurant-app-session'

function useStoredSession() {
  const [session, setSession] = useState<Tokens | null>(() => {
    const raw = window.localStorage.getItem(storageKey)
    return raw ? (JSON.parse(raw) as Tokens) : null
  })

  useEffect(() => {
    if (session) {
      window.localStorage.setItem(storageKey, JSON.stringify(session))
    } else {
      window.localStorage.removeItem(storageKey)
    }
  }, [session])

  return { session, setSession }
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/staff/login" element={<StaffLoginPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/customer" element={<CustomerPage />} />
      </Routes>
    </BrowserRouter>
  )
}

function Shell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <main className="shell">
      <header className="hero-banner">
        <div>
          <p className="eyebrow">Restaurant menu system</p>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        <Link className="secondary-link" to="/">
          Home
        </Link>
      </header>
      {children}
    </main>
  )
}

function HomePage() {
  return (
    <Shell
      title="Role-based restaurant operations"
      subtitle="FastAPI powers the backend API, while React + Vite provides a lightweight mobile-first frontend for staff and customers."
    >
      <section className="card-grid hero-grid">
        <article className="panel">
          <h2>Backend</h2>
          <p>Python FastAPI with JWT auth, OTP verification, QR table onboarding, live menu visibility, and audit logging.</p>
        </article>
        <article className="panel">
          <h2>Frontend</h2>
          <p>React + Vite + TypeScript was chosen for fast iteration, strong component reuse, and responsive role-based dashboards.</p>
        </article>
        <article className="panel panel-actions">
          <h2>Get started</h2>
          <div className="button-row">
            <Link className="button primary" to="/staff/login">
              Staff login
            </Link>
            <Link className="button secondary" to="/customer">
              Customer QR flow
            </Link>
          </div>
        </article>
      </section>
    </Shell>
  )
}

function StaffLoginPage() {
  const navigate = useNavigate()
  const { session, setSession } = useStoredSession()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('Admin@123')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (session && session.role !== 'CUSTOMER') {
      navigate('/dashboard')
    }
  }, [navigate, session])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const tokens = await apiRequest<Tokens>('/api/v1/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      setSession(tokens)
      navigate('/dashboard')
    } catch (submitError) {
      setError((submitError as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Shell title="Staff sign-in" subtitle="Admin, chef, and waitress accounts authenticate with username and password.">
      <form className="panel form" onSubmit={handleSubmit}>
        <label>
          Username
          <input value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="button primary" type="submit" disabled={submitting}>
          {submitting ? 'Signing in...' : 'Login'}
        </button>
        <p className="hint">Seeded accounts: admin/Admin@123, chef1/Password@123, waitress1/Password@123</p>
      </form>
    </Shell>
  )
}

function DashboardPage() {
  const navigate = useNavigate()
  const { session, setSession } = useStoredSession()

  useEffect(() => {
    if (!session || session.role === 'CUSTOMER') {
      navigate('/staff/login')
    }
  }, [navigate, session])

  if (!session || session.role === 'CUSTOMER') {
    return null
  }

  return (
    <Shell title={`${session.role} dashboard`} subtitle="Use the RBAC-backed workflows below to manage staff, tables, menu availability, and customer seating.">
      <div className="toolbar">
        <span className="badge">Signed in as {session.role}</span>
        <button className="button secondary" onClick={() => { setSession(null); navigate('/staff/login') }}>
          Logout
        </button>
      </div>
      {session.role === 'ADMIN' && <AdminDashboard token={session.access_token} />}
      {session.role === 'CHEF' && <ChefDashboard token={session.access_token} />}
      {session.role === 'WAITRESS' && <WaitressDashboard token={session.access_token} />}
    </Shell>
  )
}

function AdminDashboard({ token }: { token: string }) {
  const [users, setUsers] = useState<User[]>([])
  const [tables, setTables] = useState<Table[]>([])
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [occupancy, setOccupancy] = useState<TableSession[]>([])
  const [message, setMessage] = useState('')
  const [userForm, setUserForm] = useState({ username: '', password: '', role: 'CHEF' as StaffRole })
  const [tableNumber, setTableNumber] = useState('')

  async function loadData() {
    const [usersResponse, tablesResponse, logsResponse, occupancyResponse] = await Promise.all([
      apiRequest<User[]>('/api/v1/admin/users', { token }),
      apiRequest<Table[]>('/api/v1/admin/tables', { token }),
      apiRequest<AuditLog[]>('/api/v1/admin/audit-logs', { token }),
      apiRequest<TableSession[]>('/api/v1/admin/occupancy', { token }),
    ])
    setUsers(usersResponse)
    setTables(tablesResponse)
    setLogs(logsResponse)
    setOccupancy(occupancyResponse)
  }

  useEffect(() => {
    loadData().catch((error) => setMessage(error.message))
  }, [])

  async function createUser(event: FormEvent) {
    event.preventDefault()
    try {
      await apiRequest<User>('/api/v1/admin/users', {
        method: 'POST',
        token,
        body: JSON.stringify(userForm),
      })
      setUserForm({ username: '', password: '', role: 'CHEF' })
      setMessage('Staff user created.')
      await loadData()
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function createTable(event: FormEvent) {
    event.preventDefault()
    try {
      await apiRequest<Table>('/api/v1/admin/tables', {
        method: 'POST',
        token,
        body: JSON.stringify({ table_number: tableNumber }),
      })
      setTableNumber('')
      setMessage('Table created.')
      await loadData()
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  return (
    <section className="dashboard-grid">
      <article className="panel">
        <h2>Create staff user</h2>
        <form className="form compact" onSubmit={createUser}>
          <input placeholder="username" value={userForm.username} onChange={(event) => setUserForm({ ...userForm, username: event.target.value })} />
          <input type="password" placeholder="password" value={userForm.password} onChange={(event) => setUserForm({ ...userForm, password: event.target.value })} />
          <select value={userForm.role} onChange={(event) => setUserForm({ ...userForm, role: event.target.value as StaffRole })}>
            <option value="CHEF">Chef</option>
            <option value="WAITRESS">Waitress</option>
          </select>
          <button className="button primary" type="submit">Create user</button>
        </form>
        <div className="table-wrapper">
          <table>
            <thead><tr><th>User</th><th>Role</th><th>Status</th></tr></thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}><td>{user.username}</td><td>{user.role}</td><td>{user.status}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
      <article className="panel">
        <h2>Table management</h2>
        <form className="form compact" onSubmit={createTable}>
          <input placeholder="Table number" value={tableNumber} onChange={(event) => setTableNumber(event.target.value)} />
          <button className="button primary" type="submit">Create table</button>
        </form>
        <div className="table-wrapper">
          <table>
            <thead><tr><th>Table</th><th>Status</th><th>QR payload</th></tr></thead>
            <tbody>
              {tables.map((table) => (
                <tr key={table.id}><td>{table.table_number}</td><td>{table.status}</td><td className="mono">{table.qr_code_value}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
      <article className="panel">
        <h2>Occupancy</h2>
        <div className="table-wrapper">
          <table>
            <thead><tr><th>Table</th><th>Customer</th><th>Status</th></tr></thead>
            <tbody>
              {occupancy.map((session) => (
                <tr key={`${session.id}-${session.table_id}`}><td>{session.table_number}</td><td>{session.customer_mobile_number}</td><td>{session.status}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
      <article className="panel">
        <h2>Audit logs</h2>
        {message && <p className="hint">{message}</p>}
        <ul className="audit-list">
          {logs.slice(0, 8).map((log) => (
            <li key={log.id}><strong>{log.action}</strong> · {log.entity_type} #{log.entity_id ?? 'n/a'}</li>
          ))}
        </ul>
      </article>
    </section>
  )
}

function ChefDashboard({ token }: { token: string }) {
  const [items, setItems] = useState<MenuItem[]>([])
  const [categories, setCategories] = useState<MenuCategory[]>([])
  const [message, setMessage] = useState('')
  const [form, setForm] = useState({ name: '', description: '', price: '0', category_id: '', food_type: 'VEG', stock_qty: '0' })

  async function loadData() {
    const [itemResponse, categoryResponse] = await Promise.all([
      apiRequest<MenuItem[]>('/api/v1/chef/menu-items', { token }),
      apiRequest<MenuCategory[]>('/api/v1/chef/menu-categories', { token }),
    ])
    setItems(itemResponse)
    setCategories(categoryResponse)
  }

  useEffect(() => {
    loadData().catch((error) => setMessage(error.message))
  }, [])

  async function createItem(event: FormEvent) {
    event.preventDefault()
    try {
      await apiRequest<MenuItem>('/api/v1/chef/menu-items', {
        method: 'POST',
        token,
        body: JSON.stringify({
          ...form,
          price: Number(form.price),
          stock_qty: Number(form.stock_qty),
          category_id: form.category_id ? Number(form.category_id) : null,
        }),
      })
      setForm({ name: '', description: '', price: '0', category_id: '', food_type: 'VEG', stock_qty: '0' })
      setMessage('Menu item created.')
      await loadData()
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function toggleAvailability(item: MenuItem) {
    try {
      await apiRequest<MenuItem>(`/api/v1/chef/menu-items/${item.id}/availability`, {
        method: 'PATCH',
        token,
        body: JSON.stringify({
          is_available: !item.is_available,
          stock_qty: item.is_available ? 0 : item.stock_qty ?? 10,
        }),
      })
      await loadData()
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  return (
    <section className="dashboard-grid single-column">
      <article className="panel">
        <h2>Add menu item</h2>
        <form className="form compact grid-two" onSubmit={createItem}>
          <input placeholder="Name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          <input placeholder="Description" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
          <input type="number" min="1" step="0.01" placeholder="Price" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} />
          <input type="number" min="0" placeholder="Stock" value={form.stock_qty} onChange={(event) => setForm({ ...form, stock_qty: event.target.value })} />
          <select value={form.category_id} onChange={(event) => setForm({ ...form, category_id: event.target.value })}>
            <option value="">Select category</option>
            {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </select>
          <select value={form.food_type} onChange={(event) => setForm({ ...form, food_type: event.target.value })}>
            <option value="VEG">Veg</option>
            <option value="NON_VEG">Non-veg</option>
          </select>
          <button className="button primary" type="submit">Create item</button>
        </form>
        {message && <p className="hint">{message}</p>}
      </article>
      <article className="panel">
        <h2>Live menu control</h2>
        <div className="table-wrapper">
          <table>
            <thead><tr><th>Item</th><th>Category</th><th>Type</th><th>Availability</th><th></th></tr></thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.name}</td>
                  <td>{item.category_name ?? '—'}</td>
                  <td>{item.food_type}</td>
                  <td>{item.is_available ? 'Available' : 'Unavailable'}</td>
                  <td><button className="button secondary" onClick={() => toggleAvailability(item)}>Toggle</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  )
}

function WaitressDashboard({ token }: { token: string }) {
  const [tables, setTables] = useState<TableSession[]>([])
  const [menu, setMenu] = useState<MenuItem[]>([])
  const [message, setMessage] = useState('')
  const [form, setForm] = useState({ table_id: '', mobile_number: '', override_active_session: false })

  async function loadData() {
    const [tableResponse, menuResponse] = await Promise.all([
      apiRequest<TableSession[]>('/api/v1/waitress/tables/status', { token }),
      apiRequest<MenuItem[]>('/api/v1/waitress/menu', { token }),
    ])
    setTables(tableResponse)
    setMenu(menuResponse)
  }

  useEffect(() => {
    loadData().catch((error) => setMessage(error.message))
  }, [])

  async function registerCustomer(event: FormEvent) {
    event.preventDefault()
    try {
      await apiRequest<TableSession>('/api/v1/waitress/table/register-customer', {
        method: 'POST',
        token,
        body: JSON.stringify({
          table_id: Number(form.table_id),
          mobile_number: form.mobile_number,
          override_active_session: form.override_active_session,
        }),
      })
      setForm({ table_id: '', mobile_number: '', override_active_session: false })
      setMessage('Customer registered to table.')
      await loadData()
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function offboard(tableSessionId: number) {
    try {
      await apiRequest<TableSession>('/api/v1/waitress/table/offboard', {
        method: 'POST',
        token,
        body: JSON.stringify({ table_session_id: tableSessionId }),
      })
      await loadData()
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  const availableTables = useMemo(() => tables.filter((table) => table.status !== 'ACTIVE'), [tables])

  return (
    <section className="dashboard-grid">
      <article className="panel">
        <h2>Assisted seating</h2>
        <form className="form compact" onSubmit={registerCustomer}>
          <select value={form.table_id} onChange={(event) => setForm({ ...form, table_id: event.target.value })}>
            <option value="">Select a free table</option>
            {availableTables.map((table) => <option key={table.table_id} value={table.table_id}>{table.table_number}</option>)}
          </select>
          <input placeholder="Customer mobile number" value={form.mobile_number} onChange={(event) => setForm({ ...form, mobile_number: event.target.value })} />
          <label className="checkbox-row">
            <input type="checkbox" checked={form.override_active_session} onChange={(event) => setForm({ ...form, override_active_session: event.target.checked })} />
            Allow waitress override
          </label>
          <button className="button primary" type="submit">Register customer</button>
        </form>
        {message && <p className="hint">{message}</p>}
      </article>
      <article className="panel">
        <h2>Live occupancy board</h2>
        <div className="table-wrapper">
          <table>
            <thead><tr><th>Table</th><th>Customer</th><th>Status</th><th></th></tr></thead>
            <tbody>
              {tables.map((table) => (
                <tr key={`${table.table_id}-${table.id}`}>
                  <td>{table.table_number}</td>
                  <td>{table.customer_mobile_number}</td>
                  <td>{table.status}</td>
                  <td>{table.status === 'ACTIVE' ? <button className="button secondary" onClick={() => offboard(table.id)}>Offboard</button> : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
      <article className="panel">
        <h2>Current menu availability</h2>
        <ul className="menu-list">
          {menu.map((item) => (
            <li key={item.id}><strong>{item.name}</strong> · {item.is_available ? 'Available' : 'Unavailable'} · {item.food_type}</li>
          ))}
        </ul>
      </article>
    </section>
  )
}

function CustomerPage() {
  const [searchParams] = useSearchParams()
  const qr = searchParams.get('qr') ?? ''
  const { session, setSession } = useStoredSession()
  const [mobileNumber, setMobileNumber] = useState('9999999999')
  const [otpCode, setOtpCode] = useState('')
  const [resolvedTable, setResolvedTable] = useState<Table | null>(null)
  const [menu, setMenu] = useState<MenuItem[]>([])
  const [demoOtp, setDemoOtp] = useState('')
  const [foodType, setFoodType] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!qr) {
      setMessage('Append a valid ?qr=... value from the admin dashboard to simulate a table scan.')
      return
    }
    apiRequest<Table>(`/api/v1/customer/table/resolve?qr=${encodeURIComponent(qr)}`)
      .then(setResolvedTable)
      .catch((error) => setMessage(error.message))
  }, [qr])

  useEffect(() => {
    if (session?.role === 'CUSTOMER') {
      const suffix = foodType ? `&foodType=${foodType}` : ''
      apiRequest<MenuItem[]>(`/api/v1/customer/menu?available=true${suffix}`, { token: session.access_token })
        .then(setMenu)
        .catch((error) => setMessage(error.message))
    }
  }, [session, foodType])

  async function requestOtp() {
    try {
      const response = await apiRequest<{ otp_code?: string; message: string }>('/api/v1/customer/auth/request-otp', {
        method: 'POST',
        body: JSON.stringify({ mobile_number: mobileNumber }),
      })
      setDemoOtp(response.otp_code ?? '')
      setMessage(response.message)
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  async function verifyOtp(event: FormEvent) {
    event.preventDefault()
    try {
      const tokens = await apiRequest<Tokens>('/api/v1/customer/auth/verify-otp', {
        method: 'POST',
        body: JSON.stringify({ mobile_number: mobileNumber, otp_code: otpCode, qr_code_value: qr }),
      })
      setSession(tokens)
      setMessage('Customer authenticated. Live menu unlocked.')
    } catch (error) {
      setMessage((error as Error).message)
    }
  }

  return (
    <Shell title="Customer QR onboarding" subtitle="Scan a table QR code, verify with OTP, and view the menu items that are currently available.">
      <section className="dashboard-grid single-column">
        <article className="panel">
          <h2>Table context</h2>
          <p>{resolvedTable ? `Resolved ${resolvedTable.table_number}` : 'Waiting for a valid QR payload.'}</p>
          <p className="mono">{qr || 'No qr query parameter supplied.'}</p>
        </article>
        <article className="panel form">
          <h2>OTP login</h2>
          <div className="button-row">
            <input value={mobileNumber} onChange={(event) => setMobileNumber(event.target.value)} />
            <button className="button secondary" onClick={requestOtp}>Request OTP</button>
          </div>
          {demoOtp && <p className="hint">Demo OTP: {demoOtp}</p>}
          <form className="button-row" onSubmit={verifyOtp}>
            <input placeholder="Enter OTP" value={otpCode} onChange={(event) => setOtpCode(event.target.value)} />
            <button className="button primary" type="submit">Verify & assign table</button>
          </form>
          {message && <p className="hint">{message}</p>}
        </article>
        <article className="panel">
          <div className="row-between">
            <h2>Live menu</h2>
            <select value={foodType} onChange={(event) => setFoodType(event.target.value)}>
              <option value="">All</option>
              <option value="VEG">Veg</option>
              <option value="NON_VEG">Non-veg</option>
            </select>
          </div>
          <div className="card-grid">
            {menu.map((item) => (
              <article className="menu-card" key={item.id}>
                <div className="row-between"><h3>{item.name}</h3><span>{item.food_type}</span></div>
                <p>{item.description}</p>
                <p>{item.category_name ?? 'General'} · ${item.price.toFixed(2)}</p>
              </article>
            ))}
            {menu.length === 0 && <p className="hint">Authenticate to load available items.</p>}
          </div>
        </article>
      </section>
    </Shell>
  )
}

export default App
