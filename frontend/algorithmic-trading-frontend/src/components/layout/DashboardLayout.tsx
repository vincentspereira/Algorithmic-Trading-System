import React from 'react';

type Props = {
  children: React.ReactNode;
};

const DashboardLayout = ({ children }: Props) => {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 p-4 shadow-md">
        <h1 className="text-2xl font-bold">Trading Dashboard</h1>
      </header>
      <main className="p-4">
        {children}
      </main>
    </div>
  );
};

export default DashboardLayout;