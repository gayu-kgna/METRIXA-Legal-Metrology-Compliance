import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PlusCircle, MapPin, Building, Package, ArrowRight, AlertCircle } from 'lucide-react';
import { createInspection } from '../api/inspections';
import { listProducts } from '../api/products';
import { ProductLedgerItem } from '../types/api';

export const InspectionCreatePage: React.FC = () => {
  const navigate = useNavigate();

  const [products, setProducts] = useState<ProductLedgerItem[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string>('');
  const [outletName, setOutletName] = useState<string>('');
  const [outletAddress, setOutletAddress] = useState<string>('');
  const [latitude, setLatitude] = useState<string>('');
  const [longitude, setLongitude] = useState<string>('');
  const [notes, setNotes] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchProducts() {
      try {
        const prodRes = await listProducts({ page_size: 100 });
        const items = prodRes.data || [];
        setProducts(items);
        if (items.length > 0) {
          setSelectedProductId(items[0].id);
        }
      } catch (err) {
        console.warn('Could not load products:', err);
      }
    }
    fetchProducts();
  }, []);

  const handleGetCurrentLocation = () => {
    if (navigator?.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLatitude(pos.coords.latitude.toFixed(6));
          setLongitude(pos.coords.longitude.toFixed(6));
        },
        (err) => {
          console.warn('Geolocation error:', err);
        }
      );
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!outletName.trim()) {
      setError('Retail outlet name is mandatory.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        product_id: selectedProductId || undefined,
        retail_outlet_name: outletName.trim(),
        retail_outlet_address: outletAddress.trim() || undefined,
        geo_coordinates: latitude && longitude ? {
          latitude: parseFloat(latitude),
          longitude: parseFloat(longitude),
        } : undefined,
        notes: notes.trim() || undefined,
      };

      const newInsp = await createInspection(payload);
      // Navigate directly to 6-surface capture workspace as specified in requirement 7
      navigate(`/inspections/${newInsp.id}/capture`);
    } catch (err: any) {
      setError(err.message || 'Failed to create inspection session');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container" style={{ maxWidth: 800 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: '1.75rem', marginBottom: 4 }}>
          Initialize New Inspection Session
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Record retail location metadata and select packaged commodity for Legal Metrology evaluation
        </p>
      </div>

      <div className="card">
        {error && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 14px',
            backgroundColor: 'var(--verdict-fail-bg)',
            border: '1px solid var(--verdict-fail-border)',
            borderRadius: 'var(--radius-sm)',
            color: '#FCA5A5',
            fontSize: '0.88rem',
            marginBottom: 20,
          }}>
            <AlertCircle size={16} color="var(--verdict-fail)" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Retail Outlet Section */}
          <div style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: '1.05rem', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Building size={18} color="var(--accent-cyan)" />
              <span>Inspection Location Details</span>
            </h3>

            <div className="form-group">
              <label className="form-label" htmlFor="outletName">
                Retail Outlet / Establishment Name *
              </label>
              <input
                id="outletName"
                type="text"
                className="form-input"
                placeholder="e.g. Metro Supermarket — Connaught Place Branch"
                value={outletName}
                onChange={(e) => setOutletName(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="outletAddress">
                Outlet Address / Landmark
              </label>
              <textarea
                id="outletAddress"
                className="form-textarea"
                rows={2}
                placeholder="e.g. Block B, Inner Circle, Connaught Place, New Delhi 110001"
                value={outletAddress}
                onChange={(e) => setOutletAddress(e.target.value)}
              />
            </div>

            <div className="grid-2">
              <div className="form-group">
                <label className="form-label" htmlFor="latitude">
                  GPS Latitude
                </label>
                <input
                  id="latitude"
                  type="text"
                  className="form-input"
                  placeholder="e.g. 28.6328"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="longitude">
                  GPS Longitude
                </label>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input
                    id="longitude"
                    type="text"
                    className="form-input"
                    placeholder="e.g. 77.2197"
                    value={longitude}
                    onChange={(e) => setLongitude(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={handleGetCurrentLocation}
                    className="btn btn-secondary btn-sm"
                    title="Get Current Device Coordinates"
                    style={{ whiteSpace: 'nowrap' }}
                  >
                    <MapPin size={14} />
                    <span>GPS</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Product Association Section */}
          <div style={{ marginBottom: 24, paddingTop: 16, borderTop: '1px solid var(--border-subtle)' }}>
            <h3 style={{ fontSize: '1.05rem', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Package size={18} color="var(--primary-500)" />
              <span>Packaged Commodity SKU</span>
            </h3>

            <div className="form-group">
              <label className="form-label" htmlFor="productSelect">
                Select Commodity from National Master
              </label>
              <select
                id="productSelect"
                className="form-select"
                value={selectedProductId}
                onChange={(e) => setSelectedProductId(e.target.value)}
              >
                <option value="">-- Attach Product After Scanning --</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.brand_name} {p.product_name} {p.gtin_barcode ? `[GTIN: ${p.gtin_barcode}]` : ''}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="notes">
                Officer Field Notes / Inspection Context
              </label>
              <textarea
                id="notes"
                className="form-textarea"
                rows={2}
                placeholder="e.g. Routine retail audit pursuant to Section 18 of the Legal Metrology Act, 2009."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
            <button
              type="button"
              onClick={() => navigate('/inspections')}
              className="btn btn-secondary"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary btn-lg"
              disabled={loading}
              style={{ gap: 8 }}
            >
              <span>{loading ? 'Initializing Session...' : 'Create & Proceed to Capture'}</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
