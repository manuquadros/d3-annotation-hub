import { fireEvent } from "@testing-library/svelte";
import type { UserEvent } from "@testing-library/user-event";

class MockDataTransfer {
    data = new Map<string, string>();

    setData(format: string, data: string) {
        this.data.set(format, data);
    }

    getData(format: string) {
        return this.data.get(format);
    }

    clearData() {
        this.data = new Map();
    }
}

export async function dragAndDrop(
    user: UserEvent,
    source: Element,
    target: Element,
): Promise<void> {
    await user.pointer({ target: source, keys: "[MouseLeft>]" });

    const dataTransfer = new MockDataTransfer();

    fireEvent.dragStart(source, { dataTransfer });

    fireEvent.dragEnter(target);
    fireEvent.dragOver(target, { dataTransfer });

    fireEvent.drop(target, { dataTransfer });

    fireEvent.dragEnd(source);

    await user.pointer({ target: target, keys: "[/MouseLeft]" });
}
