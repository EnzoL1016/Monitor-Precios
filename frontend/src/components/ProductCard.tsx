import React, { useState } from 'react';
import { Product } from '../types';
import {
  ExternalLink, TrendingDown, Target, Zap, Trash2,
  RotateCcw, Edit3, Check, X, Globe, AlertCircle, PackageX
} from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';
import api from '../services/api';

interface ProductCardProps {
  product: Product;
  isTrashView: boolean;
  onActionSuccess: () => void;
}

export const ProductCard: React.FC<ProductCardProps> = ({ product, isTrashView, onActionSuccess }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [newTargetPrice, setNewTargetPrice] = useState(product.target_price);

  const currentPriceNum = product.current_price ? parseFloat(product.current_price.toString()) : null;
  const targetPriceNum = parseFloat(product.target_price.toString());
  const isTargetMet = currentPriceNum !== null && currentPriceNum <= targetPriceNum && product.is_available;
  const isUnavailable = !product.is_available;
  const isScraperError = !product.current_price && product.name?.startsWith('Error:');

  const getHostname = (url: string) => {
    try { return new URL(url).hostname.replace('www.', ''); }
    catch { return 'Ver sitio'; }
  };

  const handleHardDelete = async () => {
    if (confirm(`¿ELIMINAR PERMANENTE "${product.name}"?`)) {
      await api.delete(`items/${product.id}/hard_delete/`);
      onActionSuccess();
    }
  };

  const handleUpdatePrice = async () => {
    await api.patch(`items/${product.id}/`, { target_price: newTargetPrice });
    setIsEditing(false);
    onActionSuccess();
  };

  // Determinar estilo de la card
  const cardBorder = isScraperError
    ? 'border-red-500/30'
    : isUnavailable
    ? 'border-yellow-500/20'
    : isTargetMet && !isTrashView
    ? 'border-green-500/20 bg-gradient-to-b from-[#1e1f20] to-[#1a2e21]'
    : 'border-[#37393b]';

  // Ícono del estado
  const statusIcon = isScraperError
    ? <AlertCircle size={18} />
    : isUnavailable
    ? <PackageX size={18} />
    : isTargetMet && !isTrashView
    ? <Zap size={18} fill="currentColor" />
    : <TrendingDown size={18} />;

  const statusIconClass = isScraperError
    ? 'bg-red-500/10 text-red-400'
    : isUnavailable
    ? 'bg-yellow-500/10 text-yellow-400'
    : isTargetMet && !isTrashView
    ? 'bg-green-500/20 text-green-400'
    : 'bg-blue-500/10 text-blue-400';

  return (
    <div className={`relative bg-[#1e1f20] rounded-[24px] border transition-all duration-300 shadow-xl group ${cardBorder}`}>
      <div className="p-5">
        <div className="flex justify-between items-start mb-4">
          <div className={`p-2 rounded-xl ${statusIconClass}`}>
            {statusIcon}
          </div>

          <div className="flex gap-1">
            {!isTrashView ? (
              <>
                <button
                  onClick={() => setIsEditing(!isEditing)}
                  className="p-2 text-gray-500 hover:text-blue-400 hover:bg-blue-400/10 rounded-lg transition-all"
                >
                  {isEditing ? <X size={16} /> : <Edit3 size={16} />}
                </button>
                <button
                  onClick={() => api.delete(`items/${product.id}/`).then(onActionSuccess)}
                  className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all opacity-0 group-hover:opacity-100"
                >
                  <Trash2 size={16} />
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => api.post(`items/${product.id}/restore/`).then(onActionSuccess)}
                  className="p-2 text-blue-400 hover:bg-blue-400/10 rounded-lg transition-all"
                >
                  <RotateCcw size={16} />
                </button>
                <button
                  onClick={handleHardDelete}
                  className="p-2 text-red-500 hover:bg-red-500/10 rounded-lg transition-all"
                >
                  <Trash2 size={16} />
                </button>
              </>
            )}
          </div>
        </div>

        <h2 className={`text-lg font-bold truncate mb-0.5 ${isScraperError ? 'text-red-400' : isUnavailable ? 'text-yellow-400' : 'text-[#e3e3e3]'}`}>
          {product.name || 'Analizando...'}
        </h2>
        <a
          href={product.url} target="_blank" rel="noreferrer"
          className="text-[10px] text-gray-500 hover:text-blue-400 flex items-center gap-1.5 mb-5 uppercase font-bold tracking-wider"
        >
          <Globe size={10} /> {getHostname(product.url)} <ExternalLink size={10} />
        </a>

        {/* Estado del producto */}
        {isScraperError ? (
          <div className="bg-red-500/5 border border-red-500/10 p-3 rounded-2xl mb-5 text-[10px] text-red-400 font-bold text-center">
            Sitio protegido o link inválido.
          </div>
        ) : isUnavailable ? (
          <div className="bg-yellow-500/5 border border-yellow-500/15 p-4 rounded-2xl mb-5 text-center">
            <PackageX size={22} className="text-yellow-500/70 mx-auto mb-1.5" />
            <p className="text-[11px] text-yellow-400 font-bold tracking-widest uppercase">Sin stock</p>
            <p className="text-[10px] text-gray-500 mt-0.5">El producto no está disponible actualmente.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 mb-5">
            <div className={`p-3 rounded-2xl border ${isTargetMet && !isTrashView ? 'border-green-500/30' : 'border-[#37393b]'} bg-[#131314]`}>
              <p className="text-[9px] text-gray-500 font-black uppercase tracking-widest mb-1 text-center">Actual</p>
              <p className={`text-xl font-black text-center ${isTargetMet && !isTrashView ? 'text-green-400' : 'text-white'}`}>
                ${currentPriceNum?.toLocaleString() ?? '---'}
              </p>
            </div>
            <div className="bg-blue-500/5 p-3 rounded-2xl border border-blue-500/10">
              <p className="text-[9px] text-blue-400 font-black uppercase tracking-widest mb-1 text-center flex items-center justify-center gap-1">
                <Target size={10} /> Objetivo
              </p>
              {isEditing ? (
                <div className="flex items-center gap-1 mt-1">
                  <input
                    type="number"
                    className="w-full bg-[#1e1f20] border border-blue-500/30 rounded px-1 text-sm font-bold text-blue-400 focus:outline-none"
                    value={newTargetPrice}
                    onChange={(e) => setNewTargetPrice(e.target.value)}
                    autoFocus
                  />
                  <button onClick={handleUpdatePrice} className="text-green-400 p-1 rounded hover:bg-green-400/10">
                    <Check size={14} />
                  </button>
                </div>
              ) : (
                <p className="text-xl font-black text-blue-400 text-center">${targetPriceNum.toLocaleString()}</p>
              )}
            </div>
          </div>
        )}

        {/* Mini gráfico de historial */}
        {product.history && product.history.length > 1 && (
          <div className="h-14 w-full opacity-40">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={product.history}>
                <YAxis hide domain={['auto', 'auto']} />
                <Line
                  type="monotone"
                  dataKey="captured_price"
                  stroke={isScraperError ? '#ef4444' : isUnavailable ? '#eab308' : isTargetMet ? '#4ade80' : '#4285f4'}
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
};