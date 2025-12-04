import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Button, Card, Input, Select, Modal, LoadingSpinner, Alert } from '../components/UI';

const InventoryPage = () => {
  const [batches, setBatches] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    product_id: '',
    batch_code: '',
    quantity: '',
    cost_per_unit: '',
    expiration_date: '',
    note: '',
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [batchesData, productsData] = await Promise.all([
        api.get('/inventory/batches?include_product=true'),
        api.get('/products?active=true'),
      ]);
      setBatches(batchesData.batches || []);
      setProducts(productsData.products || []);
      setError('');
    } catch (error) {
      setError('Error cargando datos: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEntry = async (e) => {
    e.preventDefault();
    try {
      await api.post('/inventory/entry', formData);
      setShowModal(false);
      setFormData({ product_id: '', batch_code: '', quantity: '', cost_per_unit: '', expiration_date: '', note: '' });
      loadData();
    } catch (error) {
      setError(error.message);
    }
  };

  const openEntryModal = () => {
    setFormData({ product_id: '', batch_code: '', quantity: '', cost_per_unit: '', expiration_date: '', note: '' });
    setShowModal(true);
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
        <h2 className="text-2xl font-bold text-gray-800">Inventario</h2>
        <Button onClick={openEntryModal}>+ Nueva Entrada</Button>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError('')} />}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {batches.map((batch) => (
          <Card key={batch.id}>
            <div className="space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-gray-800">{batch.product?.name || 'N/A'}</h3>
                  <p className="text-sm text-gray-500">{batch.batch_code}</p>
                </div>
                <span className={`px-3 py-1 text-lg font-bold rounded-lg ${
                  batch.quantity > 20 ? 'bg-green-100 text-green-800' :
                  batch.quantity > 5 ? 'bg-yellow-100 text-yellow-800' :
                  'bg-red-100 text-red-800'
                }`}>
                  {batch.quantity}
                </span>
              </div>

              <div className="text-sm text-gray-600 space-y-1">
                <p>💰 Costo: ${batch.cost_per_unit}/u</p>
                <p>📅 Recibido: {batch.received_date}</p>
                {batch.expiration_date && (
                  <p className={batch.is_expired ? 'text-red-600 font-semibold' : ''}>
                    ⏰ Vence: {batch.expiration_date}
                    {batch.days_until_expiry !== undefined && ` (${batch.days_until_expiry} días)`}
                  </p>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {showModal && (
        <Modal
          isOpen={showModal}
          onClose={() => setShowModal(false)}
          title="Nueva Entrada de Mercancía"
        >
          <form onSubmit={handleEntry} className="space-y-4">
            <Select
              label="Producto"
              value={formData.product_id}
              onChange={(e) => setFormData({ ...formData, product_id: e.target.value })}
              options={[
                { value: '', label: 'Seleccionar producto...' },
                ...products.map(p => ({ value: p.id, label: `${p.name} (${p.sku})` }))
              ]}
              required
            />
            <Input
              label="Código de Lote"
              value={formData.batch_code}
              onChange={(e) => setFormData({ ...formData, batch_code: e.target.value })}
              placeholder="LOTE-2025-001"
              required
            />
            <Input
              label="Cantidad"
              type="number"
              value={formData.quantity}
              onChange={(e) => setFormData({ ...formData, quantity: e.target.value })}
              required
            />
            <Input
              label="Costo por Unidad"
              type="number"
              step="0.01"
              value={formData.cost_per_unit}
              onChange={(e) => setFormData({ ...formData, cost_per_unit: e.target.value })}
              required
            />
            <Input
              label="Fecha de Expiración (opcional)"
              type="date"
              value={formData.expiration_date}
              onChange={(e) => setFormData({ ...formData, expiration_date: e.target.value })}
            />
            <Input
              label="Nota"
              value={formData.note}
              onChange={(e) => setFormData({ ...formData, note: e.target.value })}
              placeholder="Proveedor, observaciones..."
            />
            <div className="flex gap-2 justify-end pt-4">
              <Button type="button" variant="secondary" onClick={() => setShowModal(false)}>
                Cancelar
              </Button>
              <Button type="submit">Registrar Entrada</Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};

export default InventoryPage;