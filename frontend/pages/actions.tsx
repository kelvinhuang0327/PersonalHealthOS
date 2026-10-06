import { useEffect } from 'react';
import { useRouter } from 'next/router';

export default function Redirect() {
  const router = useRouter();
  useEffect(() => { router.replace('/platform/actions'); }, [router]);
  return null;
}
