import React, { useState, useEffect } from 'react';
import { Package, DollarSign, ShoppingCart, Users, Plus, BarChart3 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Card, Button } from '../components/UI';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    if (user?.role === 'gerente') {
      api.get('/admin/metrics')
        .then(data => setStats(data.metrics))
        .catch(console.error)
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [user]);

  if (loading) {
    return <div className="text-center py-8">Cargando dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-800">Dashboard</h2>
        <p className="text-gray-600 mt-1">Bienvenido, {user?.username}</p>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Productos</p>
                <p className="text-2xl font-bold text-gray-800 mt-1">{stats.products?.total || 0}</p>
                <p className="text-xs text-green-600 mt-1">{stats.products?.active || 0} activos</p>
              </div>
              <Package className="w-12 h-12 text-blue-600 opacity-20" />
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Ventas</p>
                <p className="text-2xl font-bold text-gray-800 mt-1">
                  ${stats.sales?.total_amount?.toFixed(2) || '0.00'}
                </p>
                <p className="text-xs text-gray-600 mt-1">{stats.sales?.total_tickets || 0} tickets</p>
              </div>
              <DollarSign className="w-12 h-12 text-green-600 opacity-20" />
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Tickets</p>
                <p className="text-2xl font-bold text-gray-800 mt-1">{stats.sales?.total_tickets || 0}</p>
                <p className="text-xs text-gray-600 mt-1">Ventas procesadas</p>
              </div>
              <ShoppingCart className="w-12 h-12 text-purple-600 opacity-20" />
            </div>
          </Card>

          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Usuarios</p>
                <p className="text-2xl font-bold text-gray-800 mt-1">{stats.users?.active || 0}</p>
                <p className="text-xs text-green-600 mt-1">activos</p>
              </div>
              <Users className="w-12 h-12 text-orange-600 opacity-20" />
            </div>
          </Card>
        </div>
      )}

      <Card title="Acciones Rápidas">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(user?.role === 'cajero' || user?.role === 'gerente') && (
            <Button variant="primary" icon={Plus} className="w-full justify-center">
              Nueva Venta
            </Button>
          )}
          <Button variant="secondary" icon={Package} className="w-full justify-center">
            Consultar Inventario
          </Button>
          {user?.role === 'gerente' && (
            <Button variant="secondary" icon={BarChart3} className="w-full justify-center">
              Ver Reportes
            </Button>
          )}
        </div>
      </Card>

      {stats?.outbox && (
        <Card title="Estado del Sistema">
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <p className="text-2xl font-bold text-green-600">{stats.outbox.completed}</p>
              <p className="text-sm text-gray-600 mt-1">Eventos Completados</p>
            </div>
            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <p className="text-2xl font-bold text-yellow-600">{stats.outbox.pending}</p>
              <p className="text-sm text-gray-600 mt-1">Pendientes</p>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <p className="text-2xl font-bold text-red-600">{stats.outbox.failed}</p>
              <p className="text-sm text-gray-600 mt-1">Fallidos</p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

export default Dashboard;