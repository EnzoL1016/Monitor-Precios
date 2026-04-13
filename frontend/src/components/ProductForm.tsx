import React, { useState } from 'react';
import api from '../services/api';
import { PlusCircle, Loader2, Link2, DollarSign } from 'lucide-react';

interface ProductFormProps {
  onProductAdded: () => void;
}

export const ProductForm: React.FC<ProductFormProps> = ({ onProductAdded }) => {
  const [url, setUrl] = useState('');
  const [targetPrice, setTargetPrice] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post('items/', {
        url,
        target_price: targetPrice,
      });
      setUrl('');
      setTargetPrice('');
      onProductAdded(); 
    } catch (error) {
      alert("Error al añadir el producto. Verifica la URL.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form 
      onSubmit={handleSubmit} 
      className="bg-[#1e1f20] p-8 rounded-3xl border border-[#37393b] mb-10 shadow-2xl"
    >
      <div className="flex items-center gap-3 mb-6">
        <div className="bg-blue-500/10 p-2 rounded-lg">
          <PlusCircle size={22} className="text-blue-400" />
        </div>
        <h3 className="text-xl font-semibold text-[#e3e3e3] tracking-tight">
          Monitorear nuevo producto
        </h3>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Input de URL */}
        <div className="md:col-span-7 relative group">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-blue-400 transition-colors">
            <Link2 size={18} />
          </div>
          <input
            type="url"
            placeholder="Pega el link de Mercado Libre aquí..."
            className="w-full pl-11 pr-4 py-4 rounded-2xl bg-[#131314] border border-[#37393b] text-[#e3e3e3] placeholder:text-gray-600 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
        </div>

        {/* Input de Precio */}
        <div className="md:col-span-3 relative group">
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-blue-400 transition-colors">
            <DollarSign size={18} />
          </div>
          <input
            type="number"
            placeholder="Precio objetivo"
            className="w-full pl-11 pr-4 py-4 rounded-2xl bg-[#131314] border border-[#37393b] text-[#e3e3e3] placeholder:text-gray-600 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 outline-none transition-all font-medium"
            value={targetPrice}
            onChange={(e) => setTargetPrice(e.target.value)}
            required
          />
        </div>

        {/* Botón de envío */}
        <button
          type="submit"
          disabled={loading}
          className="md:col-span-2 bg-[#d2e3fc] text-[#041e49] p-4 rounded-2xl font-bold hover:bg-white transition-all disabled:bg-gray-700 disabled:text-gray-500 flex justify-center items-center shadow-lg active:scale-95"
        >
          {loading ? <Loader2 className="animate-spin" /> : 'Trackear'}
        </button>
      </div>

      <p className="mt-4 text-xs text-gray-500 ml-1">
        El scraper analizará automáticamente el nombre y el precio actual del producto.
      </p>
    </form>
  );
};