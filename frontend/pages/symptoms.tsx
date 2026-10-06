import { useEffect } from 'react';
import { useRouter } from 'next/router';

export default function Redirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/platform/symptoms'); }, [router]);
  return null;
}
