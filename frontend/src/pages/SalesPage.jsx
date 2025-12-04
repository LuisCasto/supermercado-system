import { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
// Página de Productos
const ProductsPage = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
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
    } catch (error) {
      console.error('Error cargando productos:', error);
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
      alert(error.message);
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
      alert(error.message);
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
                    <Button variant="secondary" onClick={() => handleEdit(product)} className="text-sm">
                      Editar
                    </Button>
                    <Button variant="danger" onClick={() => handleDelete(product.id)} className="text-sm">
                      Eliminar
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
// Página de Inventario
const InventoryPage = () => {
  const [batches, setBatches] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [modalType, setModalType] = useState('entry'); // 'entry' o 'adjustment'
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
    } catch (error) {
      console.error('Error:', error);
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
      alert(error.message);
    }
  };

  const openEntryModal = () => {
    setModalType('entry');
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
// Página de Ventas (POS)
const SalesPage = () => {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState('cash');

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      const data = await api.get('/products?active=true&include_stock=true');
      setProducts(data.products || []);
    } catch (error) {
      console.error('Error:', error);
    }
  };

  const addToCart = (product) => {
    const existing = cart.find(item => item.product_id === product.id);
    if (existing) {
      setCart(cart.map(item =>
        item.product_id === product.id
          ? { ...item, quantity: item.quantity + 1 }
          : item
      ));
    } else {
      setCart([...cart, {
        product_id: product.id,
        name: product.name,
        quantity: 1,
        unit_price: product.base_price,
        total_stock: product.total_stock,
      }]);
    }
  };

  const updateQuantity = (productId, newQuantity) => {
    if (newQuantity <= 0) {
      setCart(cart.filter(item => item.product_id !== productId));
    } else {
      setCart(cart.map(item =>
        item.product_id === productId
          ? { ...item, quantity: newQuantity }
          : item
      ));
    }
  };

  const calculateTotal = () => {
    const subtotal = cart.reduce((sum, item) => sum + (item.unit_price * item.quantity), 0);
    const tax = subtotal * 0.16;
    return { subtotal, tax, total: subtotal + tax };
  };

  const handleCheckout = async () => {
    if (cart.length === 0) {
      alert('El carrito está vacío');
      return;
    }

    setLoading(true);
    try {
      const saleData = {
        items: cart.map(item => ({
          product_id: item.product_id,
          quantity: item.quantity,
          unit_price: item.unit_price,
        })),
        payment_method: paymentMethod,
        tax_rate: 0.16,
      };

      const response = await api.post('/sales', saleData);
      alert(`✅ Venta registrada exitosamente\nID: ${response.sale_id}\nTotal: ${response.grand_total}`);
      setCart([]);
      loadProducts();
    } catch (error) {
      alert(`❌ Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const { subtotal, tax, total } = calculateTotal();
  const filteredProducts = products.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.sku.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Panel de productos */}
      <div className="lg:col-span-2 space-y-4">
        <Card>
          <Input
            placeholder="Buscar productos..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </Card>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {filteredProducts.map(product => (
            <Card key={product.id} className="hover:shadow-md transition-shadow cursor-pointer">
              <div onClick={() => product.total_stock > 0 && addToCart(product)}>
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <h3 className="font-semibold text-gray-800">{product.name}</h3>
                    <p className="text-sm text-gray-500">{product.sku}</p>
                  </div>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    product.total_stock > 10 ? 'bg-green-100 text-green-800' :
                    product.total_stock > 0 ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    Stock: {product.total_stock || 0}
                  </span>
                </div>
                <p className="text-xl font-bold text-blue-600">${product.base_price}</p>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Carrito */}
      <div className="space-y-4">
        <Card title="Carrito">
          {cart.length === 0 ? (
            <p className="text-center text-gray-500 py-8">Carrito vacío</p>
          ) : (
            <div className="space-y-3">
              {cart.map(item => (
                <div key={item.product_id} className="flex justify-between items-center border-b pb-3">
                  <div className="flex-1">
                    <p className="font-medium text-sm">{item.name}</p>
                    <p className="text-xs text-gray-500">${item.unit_price} x {item.quantity}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => updateQuantity(item.product_id, item.quantity - 1)}
                      className="w-8 h-8 bg-gray-200 rounded hover:bg-gray-300"
                    >
                      -
                    </button>
                    <span className="w-8 text-center font-semibold">{item.quantity}</span>
                    <button
                      onClick={() => updateQuantity(item.product_id, item.quantity + 1)}
                      className="w-8 h-8 bg-gray-200 rounded hover:bg-gray-300"
                      disabled={item.quantity >= item.total_stock}
                    >
                      +
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Subtotal:</span>
              <span className="font-semibold">${subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>IVA (16%):</span>
              <span className="font-semibold">${tax.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-lg font-bold border-t pt-2">
              <span>Total:</span>
              <span className="text-blue-600">${total.toFixed(2)}</span>
            </div>
          </div>

          <Select
            label="Método de Pago"
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            options={[
              { value: 'cash', label: '💵 Efectivo' },
              { value: 'card', label: '💳 Tarjeta' },
              { value: 'transfer', label: '🏦 Transferencia' },
            ]}
            className="mt-4"
          />

          <Button
            onClick={handleCheckout}
            disabled={loading || cart.length === 0}
            className="w-full mt-4 justify-center"
          >
            {loading ? 'Procesando...' : `Cobrar ${total.toFixed(2)}`}
          </Button>
        </Card>
      </div>
    </div>
  );
};
import ReportsPage from './pages/ReportsPage';
import AdminPage from './pages/AdminPage';
import { LoadingSpinner } from './components/UI';

// Navbar Component
const Navbar = ({ currentPage, setCurrentPage }) => {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

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
          <div className="flex items-center space-x-8">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">🛒</span>
              <h1 className="text-xl font-bold text-gray-800">Supermercado</h1>
            </div>
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
      </div>
    </nav>
  );
};

const AppContent = () => {
  const { user, loading, isAuthenticated } = useAuth();
  const [currentPage, setCurrentPage] = useState('dashboard');

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const renderPage = () => {
    switch (currentPage) {
      case 'dashboard':
        return <Dashboard />;
      case 'products':
        return <ProductsPage />;
      case 'inventory':
        return <InventoryPage />;
      case 'sales':
        return <SalesPage />;
      case 'reports':
        return <ReportsPage />;
      case 'admin':
        return <AdminPage />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar currentPage={currentPage} setCurrentPage={setCurrentPage} />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {renderPage()}
      </main>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;