import { useEffect, useState } from 'react';

interface GeolocationState {
  coords: { latitude: number; longitude: number } | null;
  error: string | null;
  loading: boolean;
}

export function useGeolocation(): GeolocationState {
  const [state, setState] = useState<GeolocationState>({ coords: null, error: null, loading: true });

  useEffect(() => {
    if (!navigator.geolocation) {
      setState({ coords: null, error: 'Geolokatsiya qo\'llab-quvvatlanmaydi', loading: false });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setState({
          coords: { latitude: pos.coords.latitude, longitude: pos.coords.longitude },
          error: null,
          loading: false,
        });
      },
      (err) => {
        setState({ coords: null, error: err.message, loading: false });
      },
      { enableHighAccuracy: true, timeout: 8000 },
    );
  }, []);

  return state;
}
