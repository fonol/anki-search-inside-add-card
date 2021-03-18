<template>
  <ul>
    <li
      class="siac-ft-item"
      :class="[
        v && Object.keys(v).length > 0 ? 'folder' : 'file',
        opened.includes(k) ? 'open' : '', 
        openFiles.includes(prefix+k) ? 'fopen' : ''
      ]"
      v-for="(v, k) in tree"
      :key="prefix + k"
    >
      <span @click.stop="itemClicked(k)" @contextmenu="itemRightClicked($event, prefix+k)">{{k}}</span>
      <siac-md-tree-node
        @open="
          (path) => {
            $emit('open', path);
          }
        "
        v-if="v && Object.keys(v).length > 0" 
        ref="subtrees" 
        :open-files="openFiles" 
        :tree="v"
        :prefix="prefix + k + '/'"
      ></siac-md-tree-node>
    </li>
  </ul>
</template>

<script>
export default {
  name: "siac-md-tree-node",
  props: ["tree", "prefix", "openFiles"],
  data() {
    return {
      opened: [],
    };
  },
  created() {},
  mounted() {},
  methods: {
    
    expandAll() {
        this.opened = Object.keys(this.tree);
        (this.$refs.subtrees||[]).forEach(element => {
            element.expandAll();
        });

    },
    collapseAll() {
        this.opened = [];
        (this.$refs.subtrees||[]).forEach(element => {
            element.collapseAll();
        });
    },

    itemClicked(key) {
      if (
        key in this.$props.tree &&
        Object.keys(this.$props.tree[key]).length === 0
      ) {
        this.$emit("open", this.$props.prefix + key);
      } else {
        if (this.opened.includes(key)) {
          this.opened.splice(this.opened.indexOf(key), 1);
        } else {
          this.opened.push(key);
        }
      }
    },
    itemRightClicked(event, key) {
        event.preventDefault();
        if (document.getElementById('siac-md-ctxmenu')) {
            document.getElementById('siac-md-ctxmenu').parentNode.removeChild(document.getElementById('siac-md-ctxmenu'));
        }
        let menu = document.createElement("div");
        menu.id = "siac-md-ctxmenu";
        menu.classList.add("contextmenu");
        menu.classList.add("siac-note-outer");
        menu.style.top = event.clientY + 'px';
        menu.style.left = event.clientX + 'px';

        let k = window.SIAC.Helpers.b64EncodeUnicode(key);
        // .md file
        if (key.endsWith(".md")) {
            menu.innerHTML = `
                <div class='ctx-it fg-red' onclick='window.ftreeVue.$refs.mdComp.deleteFile("${k}")'><i class='fa fa-trash mr-5'></i>Delete file</div>
            `;
        } else
        // folder
         {
            menu.innerHTML = `
                <div class='ctx-it' onclick='window.ftreeVue.$refs.mdComp.createFile("${k}")'><i class='fa fa-plus mr-5'></i>New file</div>
            `;

        }
        document.body.appendChild(menu);
        window.siacCtxMousedown = function(event) {
            if (event.target.classList.contains('ctx-it')) {
                return;
            }
            if (document.getElementById("siac-md-ctxmenu")) {
                document.getElementById("siac-md-ctxmenu").parentNode.removeChild(document.getElementById('siac-md-ctxmenu'));
            }
            document.removeEventListener("mousedown", window.siacCtxMousedown, false);

        };
        document.addEventListener("mousedown", window.siacCtxMousedown, false);
        
    }
  },
  watch: {
   
  }
};
</script>

<style scoped>
.siac-ft-item {
  list-style-type: none;
  user-select: none;
}
.siac-ft-item > span {
  padding: 0 4px;
}
.siac-ft-item > span:hover {
  background: #545454;
  color: white;
}
.siac-ft-item.file.fopen > span {
  background: #545454;
  color: white;
}
.siac-ft-item.folder {
}
.siac-ft-item.folder > ul {
  display: none;
}
.siac-ft-item.folder.open > ul {
  display: block;
}
.siac-ft-item.file {
}
.siac-ft-item.folder::before {
  background: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAg0lEQVQ4T+2TsQ2EQAwEZyMaIqQEYjIy+oDri/w7+FYIFx0SiAAM0n34zizZ47W1FoWhwn5kewLGC9AHGCR9oyEZYCBdFPXAAnQR5ABIykqOsN0AM1AFCtItIDfZboE6AIwhINp9v90fwA+P+GDpbLaz7fd8U3Bn5Tdvksqf6c2YqGYFJnBg62F1C1UAAAAASUVORK5CYII=");
  content: "";
  display: inline-block;
  height: 16px;
  width: 16px;
  margin-right: 4px;
  vertical-align: middle;
}
.siac-ft-item.folder.open::before {
  background: url("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAA1ElEQVQ4T6XTLQ7CQBCG4ffzhFNwAgQBVHFIEEhELRfA0hOAx1SgUL0BJATFETgBB0APmYSS0mx/kq6dzrPf7k5Fx6WO/cjM+sCwDEm6tsEduABR4ONE0q4JccCAWXFHM1sBZyAJAE8gk/T2WhDwwhfZBABPO5L0qAWqopcT/yUwM4/t8duu7Q8ABsCx4twh0O8uKgL+GqmkuGl7M+sBN+CaAwdgAYwlvVoAe2AOTHLAe2JJaYvmKXAHlpKyukGqs06S1vkzBke5rrs4dN1/pqYzN9U/Gipg2VQ6H+sAAAAASUVORK5CYII=");
}
.siac-ft-item > span {
  vertical-align: middle;
}
.siac-ft-item > ul {
  padding-left: 20px !important;
}
.siac-ft-item:empty {
  display: none !important;
}
</style>
<style>
.contextmenu {
    position: absolute;
    padding: 10px;
    margin: 0 !important;
    min-width: 100px;
}
.contextmenu > div {
    cursor: pointer;
}
</style>
