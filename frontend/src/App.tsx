import React, { useEffect, useState } from 'react';
import api from './services/api';
import { Product } from './types';
import { ProductForm } from './components/ProductForm';
import { ProductCard } from './components/ProductCard';
import { Login } from './components/Login';
import { 
  RefreshCcw, LogOut, LayoutDashboard, Trash2, ArrowLeft, 
  Loader2, PiggyBank, TrendingDown, Package, Search 
} from 'lucide-react';

const App: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [view, setView] = useState<'dashboard' | 'trash'>('dashboard');
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('access_token'));

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const endpoint = view === 'dashboard' ? 'items/' : 'items/trash/';
      const response = await api.get<Product[]>(endpoint);
      setProducts(response.data);
    } catch (error) {
      console.error("Error al cargar datos");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) fetchProducts();
  }, [isAuthenticated, view]);

  // FILTRADO DE PRODUCTOS (Para la barra de búsqueda)
  const filteredProducts = products.filter(p => 
    p.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    p.url.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // LÓGICA DE ESTADÍSTICAS CORREGIDA
  const stats = {
    total: products.length,
    onSale: products.filter(p => {
      const current = p.current_price ? parseFloat(p.current_price.toString()) : null;
      const target = parseFloat(p.target_price.toString());
      return current !== null && current <= target;
    }).length,
    potentialSavings: products.reduce((acc, p) => {
      const current = p.current_price ? parseFloat(p.current_price.toString()) : null;
      const target = parseFloat(p.target_price.toString());
      if (current !== null && current <= target) {
        return acc + (target - current);
      }
      return acc;
    }, 0)
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) return <Login onLoginSuccess={() => setIsAuthenticated(true)} />;

  return (
    <div className="min-h-screen bg-[#131314] text-[#e3e3e3] p-4 md:p-8 font-sans transition-colors duration-500">
      <div className="max-w-7xl mx-auto">
        
        {/* Header con navegación Dashboard/Trash */}
        <header className="flex justify-between items-center mb-10">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-2xl ${view === 'dashboard' ? 'bg-blue-500/10 text-blue-400' : 'bg-red-500/10 text-red-400'}`}>
              {view === 'dashboard' ? <LayoutDashboard size={28} /> : <Trash2 size={28} />}
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight">
                {view === 'dashboard' ? 'Mis Monitores' : 'Papelera'}
              </h1>
              <p className="text-gray-500 text-[10px] font-bold uppercase tracking-widest">
                {view === 'dashboard' ? 'Rastreo Activo' : 'Borrados recientemente'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button 
              onClick={() => { setView(view === 'dashboard' ? 'trash' : 'dashboard'); setSearchTerm(''); }}
              className="p-2.5 px-4 bg-[#1e1f20] rounded-xl text-gray-400 hover:text-white border border-[#37393b] flex items-center gap-2 transition-all text-sm font-bold shadow-sm"
            >
              {view === 'dashboard' ? <><Trash2 size={18} /> Papelera</> : <><ArrowLeft size={18} /> Volver</>}
            </button>
            <button 
              onClick={handleLogout} 
              className="p-2.5 bg-red-500/10 text-red-400 rounded-xl border border-red-500/10 hover:bg-red-500/20 transition-all shadow-sm"
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>

        {/* Dashboard de Estadísticas */}
        {view === 'dashboard' && products.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
            <div className="bg-[#1e1f20] border border-[#37393b] p-6 rounded-[28px] flex items-center gap-5">
              <div className="bg-blue-500/10 p-3.5 rounded-2xl text-blue-400"><Package size={26}/></div>
              <div>
                <p className="text-[10px] text-gray-500 font-black uppercase tracking-widest mb-0.5">Total</p>
                <p className="text-2xl font-black text-white">{stats.total}</p>
              </div>
            </div>
            
            <div className="bg-[#1e1f20] border border-[#37393b] p-6 rounded-[28px] flex items-center gap-5 transition-all hover:border-green-500/30">
              <div className="bg-green-500/10 p-3.5 rounded-2xl text-green-400"><TrendingDown size={26}/></div>
              <div>
                <p className="text-[10px] text-gray-500 font-black uppercase tracking-widest mb-0.5">En Oferta</p>
                <p className="text-2xl font-black text-green-400">{stats.onSale}</p>
              </div>
            </div>

            <div className="bg-[#1e1f20] border border-blue-500/20 p-6 rounded-[28px] flex items-center gap-5 shadow-lg shadow-blue-500/5">
              <div className="bg-blue-400 text-[#041e49] p-3.5 rounded-2xl shadow-inner"><PiggyBank size={26}/></div>
              <div>
                <p className="text-[10px] text-blue-400/70 font-black uppercase tracking-widest mb-0.5">Ahorro Total</p>
                <p className="text-2xl font-black text-white">${stats.potentialSavings.toLocaleString()}</p>
              </div>
            </div>
          </div>
        )}

        {/* Barra de Búsqueda */}
        {view === 'dashboard' && products.length > 0 && (
          <div className="relative mb-8 group">
            <div className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-blue-400 transition-colors">
              <Search size={20} />
            </div>
            <input 
              type="text"
              placeholder="Buscar por nombre o URL..."
              className="w-full pl-14 pr-5 py-4 bg-[#1e1f20] border border-[#37393b] rounded-[20px] focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all text-[#e3e3e3] placeholder:text-gray-600 shadow-inner"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        )}

        {view === 'dashboard' && <ProductForm onProductAdded={fetchProducts} />}

        {/* Listado de Productos */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {loading ? (
            <div className="col-span-full flex justify-center py-20"><Loader2 className="animate-spin text-blue-500" size={32} /></div>
          ) : filteredProducts.length > 0 ? (
            filteredProducts.map(p => (
              <ProductCard 
                key={p.id} 
                product={p} 
                isTrashView={view === 'trash'} 
                onActionSuccess={fetchProducts} 
              />
            ))
          ) : (
            <div className="col-span-full text-center py-20 border-2 border-dashed border-[#37393b] rounded-[32px]">
              <p className="text-gray-500 font-medium">
                {searchTerm ? `No hay resultados para "${searchTerm}"` : 'No hay productos activos para mostrar.'}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;