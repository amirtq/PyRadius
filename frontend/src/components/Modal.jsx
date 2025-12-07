import React from 'react';
import PropTypes from 'prop-types';
import { X } from 'lucide-react';

const Modal = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto overflow-x-hidden bg-slate-900/80 backdrop-blur-sm p-4 md:p-0">
      <div className="relative w-full max-w-md transform rounded-lg bg-slate-800 border border-slate-700 shadow-xl transition-all">
        <div className="flex items-center justify-between border-b border-slate-700 px-4 py-3 sm:px-6">
          <h3 className="text-lg font-medium leading-6 text-slate-100">{title}</h3>
          <button
            type="button"
            className="rounded-md bg-transparent text-slate-300 hover:text-slate-200 focus:outline-none"
            onClick={onClose}
          >
            <span className="sr-only">Close</span>
            <X className="h-6 w-6" aria-hidden="true" />
          </button>
        </div>
        <div className="px-4 py-5 sm:p-6 text-slate-200">
          {children}
        </div>
      </div>
    </div>
  );
};

Modal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  title: PropTypes.string.isRequired,
  children: PropTypes.node,
};

export default Modal;
