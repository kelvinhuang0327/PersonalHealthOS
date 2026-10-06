import { useEffect } from 'react';
import { useRouter } from 'next/router';

export default function Redirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/platform/settings/family'); }, [router]);
  return null;
}
