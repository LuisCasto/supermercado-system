import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Button, Card, Input, Modal, LoadingSpinner, Alert } from '../components/UI';

const ProductsPage = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    sku: '',
    name: '',
    description: '',
    category: '',
    base_price: '',
  });
  const { user } = useAuth();

  useEffect(() => {
    loadProducts();
  }, [search]);

  const loadProducts = async () => {
    try {
      const data = await api.get(`/products?search=${search}&include_stock=true`);
      setProducts(data.products || []);
      setError('');
    } catch (error) {
      setError('Error cargando productos: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingProduct) {
        await api.put(`/products/${editingProduct.id}`, formData);
      } else {
        await api.post('/products', formData);
      }
      setShowModal(false);
      setFormData({ sku: '', name: '', description: '', category: '', base_price: '' });
      setEditingProduct(null);
      loadProducts();
    } catch (error) {
      setError(error.message);
    }
  };

  const handleEdit = (product) => {
    setEditingProduct(product);
    setFormData({
      sku: product.sku,
      name: product.name,
      description: product.description || '',
      category: product.category || '',
      base_price: product.base_price,
    });
    setShowModal(true);
  };

  const handleDelete = async (productId) => {
    if (!confirm('¿Estás seguro de desactivar este producto?')) return;
    try {
      await api.delete(`/products/${productId}`);
      loadProducts();
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
        <h2 className="text-2xl font-bold text-gray-800">Productos</h2>
        {user?.role === 'gerente' && (
          <Button
            onClick={() => {
              setEditingProduct(null);
              setFormData({ sku: '', name: '', description: '', category: '', base_price: '' });
              setShowModal(true);
            }}
          >
            + Nuevo Producto
          </Button>
        )}
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError('')} />}

      <Card>
        <Input
          placeholder="Buscar productos por nombre o SKU..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {products.map((product) => (
          <Card key={product.id}>
            <div className="space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-gray-800">{product.name}</h3>
                  <p className="text-sm text-gray-500">{product.sku}</p>
                </div>
                <span className={`px-2 py-1 text-xs rounded-full ${
                  product.active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {product.active ? 'Activo' : 'Inactivo'}
                </span>
              </div>

              {product.description && (
                <p className="text-sm text-gray-600">{product.description}</p>
              )}

              {product.category && (
                <p className="text-xs text-gray-500">📁 {product.category}</p>
              )}

              <div className="flex justify-between items-center pt-3 border-t">
                <div>
                  <p className="text-lg font-bold text-blue-600">${product.base_price}</p>
                  {product.total_stock !== undefined && (
                    <p className="text-xs text-gray-500">Stock: {product.total_stock}</p>
                  )}
                </div>
                {user?.role === 'gerente' && (
                  <div className="flex gap-2">
                    <Button variant="secondary" onClick={() => handleEdit(product)} className="text-sm px-3 py-1">
                      ✏️
                    </Button>
                    <Button variant="danger" onClick={() => handleDelete(product.id)} className="text-sm px-3 py-1">
                      🗑️
                    </Button>
                  </div>
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
          title={editingProduct ? 'Editar Producto' : 'Nuevo Producto'}
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="SKU"
              value={formData.sku}
              onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
              required
              disabled={!!editingProduct}
            />
            <Input
              label="Nombre"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
            <Input
              label="Descripción"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
            <Input
              label="Categoría"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
            />
            <Input
              label="Precio Base"
              type="number"
              step="0.01"
              value={formData.base_price}
              onChange={(e) => setFormData({ ...formData, base_price: e.target.value })}
              required
            />
            <div className="flex gap-2 justify-end pt-4">
              <Button type="button" variant="secondary" onClick={() => setShowModal(false)}>
                Cancelar
              </Button>
              <Button type="submit">
                {editingProduct ? 'Actualizar' : 'Crear'}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};

export default ProductsPage;