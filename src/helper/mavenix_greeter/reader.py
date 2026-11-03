import os
import stat
import sys
import tarfile

MAX_FILES = 6000
MAX_DEPTH = 4


def add_file(tar, path, name):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode):
            return
        info = tarfile.TarInfo(name)
        info.size = st.st_size
        tar.addfile(info, f)


def walk(tar, base, rel, depth, count):
    if depth > MAX_DEPTH:
        return count
    with os.scandir(os.path.join(base, rel) if rel else base) as it:
        for entry in sorted(it, key=lambda e: e.name):
            if count >= MAX_FILES:
                return count
            name = f"{rel}/{entry.name}" if rel else entry.name
            if entry.is_symlink():
                info = tarfile.TarInfo(name)
                info.type = tarfile.SYMTYPE
                info.linkname = os.readlink(entry.path)
                tar.addfile(info)
            elif entry.is_dir(follow_symlinks=False):
                count = walk(tar, base, name, depth + 1, count)
            elif entry.is_file(follow_symlinks=False):
                try:
                    add_file(tar, entry.path, name)
                except OSError:
                    continue
            count += 1
    return count


def main():
    base = sys.argv[1]
    st = os.lstat(base)
    if not stat.S_ISDIR(st.st_mode):
        print("[reader] refused reason=not_a_directory", file=sys.stderr)
        return 1
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|") as tar:
        walk(tar, base, "", 0, 0)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OSError as e:
        print(f"[reader] refused reason={e.__class__.__name__}", file=sys.stderr)
        sys.exit(1)
