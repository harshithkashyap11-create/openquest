import { useCallback, useEffect, useRef, useState } from 'react';

export default function useAsyncData(loader, key = '') {
  const requestId = useRef(0);
  const [result, setResult] = useState({
    key: null,
    data: null,
    loading: true,
    error: null,
  });

  const reload = useCallback(async () => {
    const currentRequest = ++requestId.current;
    setResult((current) => ({
      key,
      data: current.key === key ? current.data : null,
      loading: true,
      error: null,
    }));
    try {
      const data = await loader();
      if (currentRequest === requestId.current) {
        setResult({ key, data, loading: false, error: null });
      }
    } catch (loadError) {
      if (currentRequest === requestId.current) {
        setResult((current) => ({
          key,
          data: current.key === key ? current.data : null,
          loading: false,
          error: loadError,
        }));
      }
    }
  }, [key, loader]);

  useEffect(() => {
    let active = true;
    const currentRequest = ++requestId.current;
    loader()
      .then((data) => {
        if (active && currentRequest === requestId.current) {
          setResult({ key, data, loading: false, error: null });
        }
      })
      .catch((error) => {
        if (active && currentRequest === requestId.current) {
          setResult({ key, data: null, loading: false, error });
        }
      });
    return () => {
      active = false;
      requestId.current += 1;
    };
  }, [key, loader]);

  const current = result.key === key;
  return {
    data: current ? result.data : null,
    loading: !current || result.loading,
    error: current ? result.error : null,
    reload,
  };
}
