'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { TrendingUp } from 'lucide-react';
import { api } from '@/lib/api';
import { setToken } from '@/lib/auth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [justRegistered, setJustRegistered] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('registered') === '1') {
      setJustRegistered(true);
      window.history.replaceState({}, '', '/login');
    }
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { access_token } = await api.auth.login(email.trim(), password);
      setToken(access_token);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de connexion');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center gap-2 mb-8">
          <TrendingUp className="w-7 h-7 text-indigo-400" />
          <h1 className="text-xl font-bold text-zinc-100">CS2 Skin Tracker</h1>
        </div>

        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
          <h2 className="text-base font-semibold text-zinc-100 mb-4">Connexion</h2>

          {justRegistered && (
            <div className="mb-4 rounded-md bg-green-900/20 border border-green-800/40 px-3 py-2 text-xs text-green-400">
              Compte créé — connecte-toi pour continuer
            </div>
          )}

          {error && (
            <div className="mb-4 rounded-md bg-red-900/20 border border-red-800/40 px-3 py-2 text-xs text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ton@email.com"
              required
              autoComplete="email"
            />
            <Input
              label="Mot de passe"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="current-password"
            />
            <Button type="submit" loading={loading} className="w-full justify-center">
              Se connecter
            </Button>
          </form>
        </div>

        <p className="mt-4 text-center text-xs text-zinc-500">
          Pas encore de compte ?{' '}
          <Link
            href="/register"
            className="text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            S'inscrire
          </Link>
        </p>
      </div>
    </div>
  );
}
