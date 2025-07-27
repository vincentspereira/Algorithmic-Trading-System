"use client";

import React, { useState } from 'react';

const OrderEntryForm = () => {
  const [symbol, setSymbol] = useState('');
  const [quantity, setQuantity] = useState('');
  const [orderType, setOrderType] = useState('Market');
  const [price, setPrice] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle form submission
    console.log({ symbol, quantity, orderType, price });
  };

  return (
    <form onSubmit={handleSubmit} className="bg-gray-800 p-4 rounded-md shadow-md">
      <h2 className="text-xl font-bold mb-4">Order Entry</h2>
      <div className="mb-4">
        <label htmlFor="symbol" className="block mb-1">Symbol</label>
        <input
          type="text"
          id="symbol"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2"
        />
      </div>
      <div className="mb-4">
        <label htmlFor="quantity" className="block mb-1">Quantity</label>
        <input
          type="number"
          id="quantity"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2"
        />
      </div>
      <div className="mb-4">
        <label htmlFor="orderType" className="block mb-1">Order Type</label>
        <select
          id="orderType"
          value={orderType}
          onChange={(e) => setOrderType(e.target.value)}
          className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2"
        >
          <option>Market</option>
          <option>Limit</option>
        </select>
      </div>
      {orderType === 'Limit' && (
        <div className="mb-4">
          <label htmlFor="price" className="block mb-1">Price</label>
          <input
            type="number"
            id="price"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2"
          />
        </div>
      )}
      <button type="submit" className="bg-blue-600 hover:bg-blue-700 rounded-md px-4 py-2 w-full">
        Place Order
      </button>
    </form>
  );
};

export default OrderEntryForm;