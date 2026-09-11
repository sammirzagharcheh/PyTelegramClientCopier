import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MappingTableActions } from './MappingTableActions';

describe('MappingTableActions', () => {
  it('calls onClone when Clone mapping is clicked', () => {
    const onClone = vi.fn();
    render(
      <MemoryRouter>
        <MappingTableActions
          mappingId={3}
          onEdit={vi.fn()}
          onDelete={vi.fn()}
          onClone={onClone}
        />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Clone mapping' }));
    expect(onClone).toHaveBeenCalledTimes(1);
  });
});
