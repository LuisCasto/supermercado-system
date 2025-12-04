import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Button, Card, LoadingSpinner, Alert } from '../components/UI';

const AdminPage = () => {
  const [metrics, setMetrics] = useState(null);
  const [outboxStats, setOutboxStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [metricsData, outboxData] = await Promise.all([
        api.get('/admin/metrics'),
        api.get('/admin/outbox/stats'),
      ]);
      setMetrics(metricsData.metrics);
      setOutboxStats(outboxData);
      setError('');
    } catch (error) {
      setError('Error cargando datos de administración: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const processOutbox = async () => {
    try {
      await api.post('/admin/outbox/process-now');
      alert('✅ Outbox procesado manualmente');
      loadData();
    } catch (error) {
      setError(error.message);
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
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-800">Administración</h2>
        <Button onClick={processOutbox}>🔄 Procesar Outbox</Button>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError('')} />}

      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <Card>
            <div>
              <p className="text-sm text-gray-600">Productos</p>
              <p className="text-2xl font-bold text-gray-800 mt-2">{metrics.products?.total || 0}</p>
              <p className="text-xs text-green-600 mt-1">{metrics.products?.active || 0} activos</p>
            </div>
          </Card>
          <Card>
            <div>
              <p className="text-sm text-gray-600">Lotes de Inventario</p>
              <p className="text-2xl font-bold text-gray-800 mt-2">{metrics.inventory?.total_batches || 0}</p>
              <p className="text-xs text-gray-600 mt-1">registrados</p>
            </div>
          </Card>
          <Card>
            <div>
              <p className="text-sm text-gray-600">Usuarios</p>
              <p className="text-2xl font-bold text-gray-800 mt-2">{metrics.users?.total || 0}</p>
              <p className="text-xs text-green-600 mt-1">{metrics.users?.active || 0} activos</p>
            </div>
          </Card>
          <Card>
            <div>
              <p className="text-sm text-gray-600">Tickets Vendidos</p>
              <p className="text-2xl font-bold text-gray-800 mt-2">{metrics.sales?.total_tickets || 0}</p>
              <p className="text-xs text-gray-600 mt-1">ventas procesadas</p>
            </div>
          </Card>
        </div>
      )}

      {outboxStats && (
        <Card title="Estado del Outbox">
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <p className="text-2xl font-bold text-yellow-600">{outboxStats.pending || 0}</p>
              <p className="text-sm text-gray-600 mt-1">Pendientes</p>
            </div>
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <p className="text-2xl font-bold text-blue-600">{outboxStats.processing || 0}</p>
              <p className="text-sm text-gray-600 mt-1">Procesando</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <p className="text-2xl font-bold text-green-600">{outboxStats.completed || 0}</p>
              <p className="text-sm text-gray-600 mt-1">Completados</p>
            </div>
            <div className="text-center p-4 bg-red-50 rounded-lg">
              <p className="text-2xl font-bold text-red-600">{outboxStats.failed || 0}</p>
              <p className="text-sm text-gray-600 mt-1">Fallidos</p>
            </div>
          </div>

          {outboxStats.recent_failures && outboxStats.recent_failures.length > 0 && (
            <div className="mt-4">
              <h4 className="font-semibold text-gray-700 mb-2">Fallos Recientes:</h4>
              <div className="space-y-2">
                {outboxStats.recent_failures.map((failure) => (
                  <div key={failure.id} className="text-sm bg-red-50 p-3 rounded">
                    <p className="font-mono text-xs text-gray-600">ID: {failure.id} - {failure.aggregate_id}</p>
                    <p className="text-red-700 mt-1">{failure.error_message}</p>
                    <p className="text-xs text-gray-500 mt-1">Intentos: {failure.retry_count}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default AdminPage;