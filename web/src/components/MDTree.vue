<template>
  <div class='flex-col oflow_hidden h-100'>
    <div>
      <div v-if="treeOpened" class="siac-file-tree siac-note-outer ml-5 mr-5 mt-5 p-10">
        <div class='bold cursor-pointer mb-10' @click="treeOpened = !treeOpened"><i class='fa fa-minus mr-10'></i><span>Files</span> </div>
        <siac-md-tree-node
          :tree="tree" 
          :open-files="Object.keys(opened)" 
          :prefix="'/'"
          @open="onOpen" 
          ref="treeNode" 
          class='siac-md-tree-outer'
        ></siac-md-tree-node>
        <div class='flex-row' style='justify-content: flex-end;'>
          <i class='fa fa-plus mr-10' @click="createRootFile" title='New file'></i>
          <i class='fa fa-chevron-down mr-10' @click="expandAll" title='Expand all'></i>
          <i class='fa fa-chevron-up' @click="collapseAll" title="Collapse all"></i>
        </div>
      </div>
      <div v-else class='siac-note-outer p-10 cursor-pointer bold ml-5 mr-5 mt-5 flex-row closed' @click="treeOpened = !treeOpened">
          <div class='flex-row' style='align-items: center;'>
              <i class='fa fa-plus mr-10'></i><span>Files</span>
          </div>
      </div>
    </div>
    <!-- Opened files -->
    <div style='overflow: auto;'>
        <div v-for="(content, path) in opened" :key="'op_' + path" class='siac-note-outer p-5 ml-5 mr-5 mb-5' >
            <div class='p-10 bold user_sel_none flex-row flex-between'>
                <div>
                    <span v-show="!(path in expandedEditors)" @click="open(path)" class="cursor-pointer"><i class='fa fa-plus mr-10'></i></span>
                    <span v-show="path in expandedEditors" @click="close(path)" class="cursor-pointer"><i class='fa fa-minus mr-10'></i></span>
                    {{path}}
                 </div>
                <div @click="remove(path)" class="close">
                    <i class='fa fa-times'></i>
                </div>
            </div>
            <div v-show="path in expandedEditors" class='ta_wrapper'>
                <textarea :id="'ei_'+path.replace(' ', '-')" :value="content">
                </textarea>
          </div>
    </div>
    <!-- Create File modal -->
    <div v-if='createPath && createPath.length' class='siac-md-create-file-modal-wrapper'>
      <div class='siac-md-create-file-modal siac-note-outer'>
        <div class='mb-20'>
          Create file in <i>{{createPath.endsWith('/') ? createPath: createPath + '/'}}</i>
        </div>
        <div class='mb-5'>Name</div>
        <input type="text" ref='finput' class='siac-input w-100' :class="[createFileNameIsValid ? 'valid' : 'invalid']"  v-model="createTitle">
        <div style='text-align: right;' class='mt-20'>
          <div class='siac-modal-btn' @click='createPath = null'>Cancel</div>
          <div class='siac-modal-btn ml-10' @click='createModalSubmit'>Ok</div>
        </div>
      </div>
    </div>
    <!-- Delete File modal -->
    <div v-if='deletePath && deletePath.length' class='siac-md-create-file-modal-wrapper'>
      <div class='siac-md-create-file-modal siac-note-outer'>
        <div class='mb-10 ta_center fg-red'><i class='fa fa-trash' style='font-size: 20px;'></i></div>
        <div class='mb-20 ta_center'>
          Delete file <i>{{deletePath}}</i>?
        </div>
        <div style='text-align: right;' class='mt-20'>
          <div class='siac-modal-btn' @click='deletePath = null'>Cancel</div>
          <div class='siac-modal-btn ml-10 fg-red' @click='deleteModalSubmit'><i class='fa fa-trash mr-5'></i>Delete</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "siac-md-tree",
  props: {},
  data() {
    return {
      tree: {},
      opened: {},
      expandedEditors: {},
      initializedEditors: [],
      treeOpened: true,

      createPath: null,
      createTitle: null,

      deletePath: null,
    };
  },
  mounted() {
    this.fetchTree();
  },
  methods: {
    fetchTree() {
      let self = this;
      window.SIAC.fetch.json((json) => {
        self.tree = json["tree"];
      }, "md-file-tree");
    },
    onOpen(path) {
      if (!(path in this.opened)) {
        this.$forceUpdate();
        let self = this;
        window.SIAC.fetch.json(
          (json) => {
            self.opened[path] = json["content"] || "";
            self.$forceUpdate();
          },
          "md-file-content",
          path
        );
      } else {
        this.remove(path);
      }
    },
    open(path) {
      if (!(path in this.expandedEditors)) {
        this.expandedEditors[path] = this.opened[path];
        if (!this.initializedEditors.includes(path)) {
          this.initializedEditors.push(path);
          window.SIAC.MD.mdSidebarEdit(
            path,
            document.getElementById("ei_" + path.replace(" ", "-"))
          );
        }
      }
      this.$forceUpdate();
    },
    close(path) {
      if (path in this.expandedEditors) {
        delete this.expandedEditors[path];
        this.$forceUpdate();
      }
    },
    remove(path) {
      window.SIAC.MD.mdSidebarDestroy(path);
      if (path in this.expandedEditors) {
        delete this.expandedEditors[path];
      }
      if (path in this.opened) {
        delete this.opened[path];
      }
      if (this.initializedEditors.includes(path)) {
        this.initializedEditors.splice(
          this.initializedEditors.indexOf(path),
          1
        );
      }
      this.$forceUpdate();
    },

    expandAll() {
      this.$refs.treeNode.expandAll();
    },
    collapseAll() {
      this.$refs.treeNode.collapseAll();
    },

    deleteFile(pathB64) {
      if (document.getElementById("siac-md-ctxmenu")) {
        document
          .getElementById("siac-md-ctxmenu")
          .parentNode.removeChild(document.getElementById("siac-md-ctxmenu"));
      }
      let path = window.SIAC.Helpers.b64DecodeUnicode(pathB64);
      this.deletePath = path;
    },
    createRootFile() {
       this.createFile(window.SIAC.Helpers.b64EncodeUnicode('/'));
    },

    createFile(pathB64) {
      if (document.getElementById("siac-md-ctxmenu")) {
        document
          .getElementById("siac-md-ctxmenu")
          .parentNode.removeChild(document.getElementById("siac-md-ctxmenu"));
      }
      let path = window.SIAC.Helpers.b64DecodeUnicode(pathB64);
      this.createTitle = '';
      this.createPath = path;
      let self = this;
      setTimeout(function() {
        self.$refs.finput.focus();
      }, 50);
      
    },
    createModalSubmit() {
      if (!this.createFileNameIsValid) {
        return;
      }
      let fpathB64 =  window.SIAC.Helpers.b64EncodeUnicode(this.createPath);
      let fnameB64 =  window.SIAC.Helpers.b64EncodeUnicode(this.createTitle);
      window.pycmd('siac-create-md-file ' + fpathB64 + ' ' + fnameB64);
      this.createTitle = null;
      this.createPath = null;
      let self = this;
      setTimeout(function(){
        self.fetchTree();
      }, 100);
    },
    deleteModalSubmit() {
      let fpathB64 =  window.SIAC.Helpers.b64EncodeUnicode(this.deletePath);
      window.pycmd("siac-delete-md-file " + fpathB64);
      this.deletePath = null;
      let self = this;
      setTimeout(function(){
        self.fetchTree();
      }, 100);
    },
   
  },
  computed: {
    createFileNameIsValid() {
      return /^[^\\/:*?"<>|.][^\\/:*?"<>|]*$/.test(this.createTitle || "");
    },
  },
};
</script>

<style scoped>
.siac-file-tree > ul {
  margin-left: 0;
  padding-left: 0;
}
.siac-md-tree-outer {
  overflow: auto;
  max-height: 300px;
}
.close {
  color: grey;
}
.close:hover {
  color: lightgrey;
}
.siac-md-create-file-modal-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
}
.siac-md-create-file-modal {
  padding: 20px;
}
input {
  font-size: 18px;
}
input.valid {
  border-color: #32d296 !important;
}
input.invalid {
  border-color: #f0506e !important;
}
</style>
<style>
.ta_wrapper .editor-toolbar {
  display: none !important;
}
.ta_wrapper .CodeMirror {
  font-size: 14px !important;
}
body.nightMode .siac-md-create-file-modal-wrapper {
  background: rgba(0, 0, 0, 0.7);
}
</style>