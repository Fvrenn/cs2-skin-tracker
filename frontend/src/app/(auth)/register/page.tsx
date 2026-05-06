'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { TrendingUp } from 'lucide-react';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

export default function RegisterPage() {
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [steamId, setSteamId] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const passwordTooShort = password.length > 0 && password.length < 6;
  const passwordMismatch = confirm.length > 0 && password !== confirm;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    if (password.length < 6) {
      setError('Le mot de passe doit contenir au moins 6 caractères');
      return;
    }
    if (password !== confirm) {
      setError('Les mots de passe ne correspondent pas');
      return;
    }

    setLoading(true);
    try {
      await api.auth.register(
        email.trim(),
        password,
        steamId.trim() || undefined,
      );
      router.push('/login?registered=1');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors de la création du compte');
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
          <h2 className="text-base font-semibold text-zinc-100 mb-4">Créer un compte</h2>

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
              autoComplete="new-password"
              error={passwordTooShort ? 'Minimum 6 caractères' : undefined}
            />
            <Input
              label="Confirmer le mot de passe"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="new-password"
              error={passwordMismatch ? 'Les mots de passe ne correspondent pas' : undefined}
            />
            <Input
              label="Steam ID (optionnel)"
              value={steamId}
              onChange={(e) => setSteamId(e.target.value)}
              placeholder="76561198XXXXXXXXX"
              autoComplete="off"
            />
            <Button
              type="submit"
              loading={loading}
              disabled={passwordTooShort || passwordMismatch}
              className="w-full justify-center"
            >
              Créer mon compte
            </Button>
          </form>
        </div>

        <p className="mt-4 text-center text-xs text-zinc-500">
          Déjà un compte ?{' '}
          <Link
            href="/login"
            className="text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            Se connecter
          </Link>
        </p>
      </div>
    </div>
  );
}
