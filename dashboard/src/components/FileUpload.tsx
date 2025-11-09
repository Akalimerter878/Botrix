import { Upload } from 'lucide-react';
import { useState, useRef } from 'react';
import { cn } from '../lib/utils';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  maxSize?: number; // in MB
  className?: string;
}

export function FileUpload({
  onFileSelect,
  accept = '.txt',
  maxSize = 5,
  className,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string>('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    setError('');

    // Check file size
    if (file.size > maxSize * 1024 * 1024) {
      setError(`File size must be less than ${maxSize}MB`);
      return;
    }

    // Check file type
    if (accept && !file.name.match(new RegExp(accept.replace('.', '\\.') + '$'))) {
      setError(`Only ${accept} files are allowed`);
      return;
    }

    onFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className={cn('space-y-2', className)}>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          'border-2 border-dashed rounded-lg p-8 transition-colors cursor-pointer',
          isDragging
            ? 'border-blue-500 bg-blue-500/10'
            : 'border-gray-700 hover:border-gray-600 bg-gray-800/50'
        )}
      >
        <div className="flex flex-col items-center justify-center gap-2">
          <Upload className="w-10 h-10 text-gray-400" />
          <div className="text-center">
            <p className="text-sm text-gray-300">
              <span className="text-blue-500 font-medium">Click to upload</span> or
              drag and drop
            </p>
            <p className="text-xs text-gray-500 mt-1">
              {accept} files up to {maxSize}MB
            </p>
          </div>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={handleChange}
          className="hidden"
        />
      </div>
      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );
}
