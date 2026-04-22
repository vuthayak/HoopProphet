import React from 'react';
import { Toaster } from 'react-hot-toast';

export function ToastProvider({ children }) {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          success: { duration: 3000 },
          error: { duration: 5000 },
        }}
      />
      {children}
    </>
  );
}