import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const Navbar = ({ currentPage, setCurrentPage }) => {
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊', roles: ['gerente', 'cajero', 'inventario'] },
    { id: 'products', label: 'Productos', icon: '📦', roles: ['gerente', 'inventario'] },
    { id: 'inventory', label: 'Inventario', icon: '📋', roles: ['gerente', 'inventario'] },
    { id: 'sales', label: 'Ventas', icon: '🛒', roles: ['gerente', 'cajero'] },
    { id: 'reports', label: 'Reportes', icon: '📈', roles: ['gerente'] },
    { id: 'admin', label: 'Admin', icon: '⚙️', roles: ['gerente'] },
  ];

  const filteredItems = menuItems.filter(item => item.roles.includes(user?.role));

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo y menú desktop */}
          <div className="flex items-center space-x-8">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">🛒</span>
              <h1 className="text-xl font-bold text-gray-800">Supermercado</h1>
            </div>
            
            {/* Menú Desktop */}
            <div className="hidden md:flex space-x-1">
              {filteredItems.map(item => (
                <button
                  key={item.id}
                  onClick={() => setCurrentPage(item.id)}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    currentPage === item.id
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <span className="mr-2">{item.icon}</span>
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          {/* Usuario y logout */}
          <div className="flex items-center space-x-4">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-gray-800">{user?.username}</p>
              <p className="text-xs text-gray-500 capitalize">{user?.role}</p>
            </div>
            <button
              onClick={logout}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
            >
              Salir
            </button>
          </div>
        </div>

        {/* Menú Mobile */}
        <div className="md:hidden pb-3">
          <div className="flex flex-wrap gap-2">
            {filteredItems.map(item => (
              <button
                key={item.id}
                onClick={() => setCurrentPage(item.id)}
                className={`px-3 py-1.5 text-sm rounded-lg font-medium transition-colors ${
                  currentPage === item.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                <span className="mr-1">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;