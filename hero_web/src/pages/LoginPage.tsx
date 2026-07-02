import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { Alert, Button, Card, Input, Label, TextField } from '@heroui/react'
import { getErrorMessage } from '@/api/client'
import { register as registerApi } from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'

export function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const loginMutation = useMutation({
    mutationFn: () => login(username, password),
    onSuccess: () => navigate('/banks'),
    onError: (err) => setError(getErrorMessage(err, '登录失败')),
  })

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md items-center">
      <Card className="w-full p-6">
        <Card.Header>
          <Card.Title>登录 EXAM-MASTER</Card.Title>
          <Card.Description>React + HeroUI 考试端</Card.Description>
        </Card.Header>
        <Card.Content className="flex flex-col gap-4">
          {error ? <Alert status="danger">{error}</Alert> : null}
          <TextField isRequired>
            <Label>用户名 / 邮箱</Label>
            <Input value={username} onChange={(event) => setUsername(event.target.value)} />
          </TextField>
          <TextField isRequired type="password">
            <Label>密码</Label>
            <Input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </TextField>
        </Card.Content>
        <Card.Footer className="flex flex-col gap-3">
          <Button
            fullWidth
            variant="primary"
            isPending={loginMutation.isPending}
            onPress={() => loginMutation.mutate()}
          >
            登录
          </Button>
          <p className="text-center text-sm text-default-500">
            还没有账号？<Link to="/register">注册</Link>
          </p>
        </Card.Footer>
      </Card>
    </div>
  )
}

export function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    username: '',
    email: '',
    password: '',
    confirm_password: '',
  })
  const [error, setError] = useState<string | null>(null)

  const registerMutation = useMutation({
    mutationFn: () => registerApi(form),
    onSuccess: () => navigate('/login'),
    onError: (err) => setError(getErrorMessage(err, '注册失败')),
  })

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md items-center">
      <Card className="w-full p-6">
        <Card.Header>
          <Card.Title>注册账号</Card.Title>
        </Card.Header>
        <Card.Content className="flex flex-col gap-4">
          {error ? <Alert status="danger">{error}</Alert> : null}
          {(['username', 'email', 'password', 'confirm_password'] as const).map((field) => (
            <TextField key={field} isRequired type={field.includes('password') ? 'password' : 'text'}>
              <Label>
                {field === 'username'
                  ? '用户名'
                  : field === 'email'
                    ? '邮箱'
                    : field === 'password'
                      ? '密码'
                      : '确认密码'}
              </Label>
              <Input
                type={field.includes('password') ? 'password' : 'text'}
                value={form[field]}
                onChange={(event) => setForm((prev) => ({ ...prev, [field]: event.target.value }))}
              />
            </TextField>
          ))}
        </Card.Content>
        <Card.Footer className="flex flex-col gap-3">
          <Button
            fullWidth
            variant="primary"
            isPending={registerMutation.isPending}
            onPress={() => registerMutation.mutate()}
          >
            注册
          </Button>
          <p className="text-center text-sm text-default-500">
            已有账号？<Link to="/login">去登录</Link>
          </p>
        </Card.Footer>
      </Card>
    </div>
  )
}
