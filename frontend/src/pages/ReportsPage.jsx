import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Card, LoadingSpinner, Alert } from '../components/UI';

const ReportsPage = () => {
  const [stats, setStats] = useState(null);
  const [sales, setSales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [statsData, salesData] = await Promise.all([
        api.get('/sales/stats'),
        api.get('/sales?per_page=10'),
      ]);
      setStats(statsData);
      setSales(salesData.sales || []);
      setError('');
    } catch (error) {
      setError('Error cargando reportes: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">Reportes</h2>

      {error && <Alert type="error" message={error} onClose={() => setError('')} />}

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card>
            <div>
              <p className="text-sm text-gray-600">Total Ventas</p>
              <p className="text-3xl font-bold text-gray-800 mt-2">{stats.total_sales || 0}</p>
              <p className="text-xs text-gray-500 mt-1">tickets procesados</p>
            </div>
          </Card>
          <Card>
            <div>
              <p className="text-sm text-gray-600">Monto Total</p>
              <p className="text-3xl font-bold text-green-600 mt-2">${stats.total_amount?.toFixed(2) || '0.00'}</p>
              <p className="text-xs text-gray-500 mt-1">ventas acumuladas</p>
            </div>
          </Card>
          <Card>
            <div>
              <p className="text-sm text-gray-600">Ticket Promedio</p>
              <p className="text-3xl font-bold text-blue-600 mt-2">${stats.average_ticket?.toFixed(2) || '0.00'}</p>
              <p className="text-xs text-gray-500 mt-1">por venta</p>
            </div>
          </Card>
        </div>
      )}

      {stats?.by_payment_method && (
        <Card title="Ventas por Método de Pago">
          <div className="grid grid-cols-3 gap-4">
            {Object.entries(stats.by_payment_method).map(([method, count]) => (
              <div key={method} className="text-center p-4 bg-gray-50 rounded-lg">
                <p className="text-2xl font-bold text-gray-800">{count}</p>
                <p className="text-sm text-gray-600 mt-1 capitalize">{method}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card title="Últimas Ventas">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3">ID Venta</th>
                <th className="text-left p-3">Cajero</th>
                <th className="text-left p-3">Total</th>
                <th className="text-left p-3">Método</th>
                <th className="text-left p-3">Fecha</th>
              </tr>
            </thead>
            <tbody>
              {sales.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center py-8 text-gray-500">
                    No hay ventas registradas
                  </td>
                </tr>
              ) : (
                sales.map((sale) => (
                  <tr key={sale.sale_id} className="border-b hover:bg-gray-50">
                    <td className="p-3 font-mono text-xs">{sale.sale_id}</td>
                    <td className="p-3">{sale.cashier_name}</td>
                    <td className="p-3 font-semibold">${sale.grand_total?.toFixed(2)}</td>
                    <td className="p-3 capitalize">{sale.payment_method}</td>
                    <td className="p-3">{new Date(sale.timestamp).toLocaleString('es-MX')}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
};

export default ReportsPage;