import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Button, Card, Input, Select, Alert } from '../components/UI';

const SalesPage = () => {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [error, setError] = useState('');

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      const data = await api.get('/products?active=true&include_stock=true');
      setProducts(data.products || []);
    } catch (error) {
      setError('Error cargando productos: ' + error.message);
    }
  };

  const addToCart = (product) => {
    const existing = cart.find(item => item.product_id === product.id);
    if (existing) {
      if (existing.quantity >= product.total_stock) {
        setError('No hay suficiente stock disponible');
        return;
      }
      setCart(cart.map(item =>
        item.product_id === product.id
          ? { ...item, quantity: item.quantity + 1 }
          : item
      ));
    } else {
      setCart([...cart, {
        product_id: product.id,
        name: product.name,
        sku: product.sku,
        quantity: 1,
        unit_price: product.base_price,
        total_stock: product.total_stock,
      }]);
    }
    setError('');
  };

  const updateQuantity = (productId, newQuantity) => {
    if (newQuantity <= 0) {
      setCart(cart.filter(item => item.product_id !== productId));
    } else {
      const item = cart.find(i => i.product_id === productId);
      if (newQuantity > item.total_stock) {
        setError('Cantidad excede el stock disponible');
        return;
      }
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
      setError('El carrito está vacío');
      return;
    }

    setLoading(true);
    setError('');
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
      alert(`✅ Venta registrada exitosamente\nID: ${response.sale_id}\nTotal: $${response.grand_total.toFixed(2)}`);
      setCart([]);
      loadProducts();
    } catch (error) {
      setError(error.message);
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
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">Punto de Venta</h2>

      {error && <Alert type="error" message={error} onClose={() => setError('')} />}

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
              <Card 
                key={product.id} 
                className={`transition-shadow ${product.total_stock > 0 ? 'hover:shadow-md cursor-pointer' : 'opacity-50'}`}
              >
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
                      <p className="text-xs text-gray-500">${item.unit_price} x {item.quantity} = ${(item.unit_price * item.quantity).toFixed(2)}</p>
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
              {loading ? 'Procesando...' : `Cobrar $${total.toFixed(2)}`}
            </Button>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default SalesPage;